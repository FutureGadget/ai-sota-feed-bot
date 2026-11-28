"""Plan, merge, and validate the x-watch routine's browsed X posts.

The routine browses each `x_watch` account in config/sources/browsed.yaml and
commits the posts to data/browsed/x/<UTC date>.json; the collector's `x_watch`
type reads those files. This script owns the file format so the agent never
hand-edits the day file.

Usage:
    python x_watch.py plan                 # accounts to visit + per-account cutoff
    python x_watch.py merge --in posts.json  # validate + merge into today's file
    python x_watch.py check                # validate every committed day file

Day file shape:
    {"posts": [{"handle", "url", "text", "published", "author"?, "kind"?,
                "quoted"?: {"handle", "text", "url"}}]}
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "pipeline"))

from sources_config import BROWSED_DATA_DIR, load_sources  # noqa: E402

X_DIR = BROWSED_DATA_DIR / "x"
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")
KINDS = {"post", "thread", "quote"}
PLAN_LOOKBACK_DAYS = 7
DEFAULT_SINCE_HOURS = 48


def _handles() -> dict[str, str]:
    """Lowercase handle -> handle as written in the registry."""
    return {
        str(s["handle"]).lower(): str(s["handle"])
        for s in load_sources("browsed")
        if s.get("type") == "x_watch"
    }


def _parse_ts(value: str) -> datetime:
    ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if ts.tzinfo is None:
        raise ValueError("timestamp_without_timezone")
    return ts.astimezone(timezone.utc)


def _load_day(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("posts") or []


def validate_post(post: dict, handles: dict[str, str]) -> list[str]:
    errors = []
    handle = str(post.get("handle") or "").lstrip("@").lower()
    if handle not in handles:
        errors.append(f"unknown_handle:{post.get('handle')}")
    url = str(post.get("url") or "")
    if not re.fullmatch(rf"https://x\.com/{re.escape(handle)}/status/\d+", url, flags=re.I):
        errors.append(f"bad_url:{url}")
    if not str(post.get("text") or "").strip():
        errors.append(f"empty_text:{url}")
    try:
        _parse_ts(post.get("published") or "")
    except ValueError:
        errors.append(f"bad_published:{url}")
    if post.get("kind", "post") not in KINDS:
        errors.append(f"bad_kind:{url}")
    quoted = post.get("quoted")
    if quoted is not None and not str((quoted or {}).get("text") or "").strip():
        errors.append(f"empty_quoted_text:{url}")
    return errors


def cmd_plan(now: datetime) -> int:
    handles = _handles()
    newest: dict[str, datetime] = {}
    for back in range(PLAN_LOOKBACK_DAYS):
        day = (now - timedelta(days=back)).strftime("%Y-%m-%d")
        for post in _load_day(X_DIR / f"{day}.json"):
            h = str(post.get("handle") or "").lower()
            try:
                ts = _parse_ts(post["published"])
            except (KeyError, ValueError):
                continue
            if h not in newest or ts > newest[h]:
                newest[h] = ts
    default_since = now - timedelta(hours=DEFAULT_SINCE_HOURS)
    plan = {
        "date": now.strftime("%Y-%m-%d"),
        "accounts": [
            {
                "handle": handle,
                "url": f"https://x.com/{handle}",
                "since": max(newest.get(key, default_since), default_since).isoformat(),
            }
            for key, handle in handles.items()
        ],
    }
    print(json.dumps(plan, indent=2))
    return 0


def cmd_merge(in_path: Path, now: datetime) -> int:
    handles = _handles()
    incoming = json.loads(in_path.read_text(encoding="utf-8"))
    if isinstance(incoming, dict):
        incoming = incoming.get("posts") or []
    errors = [e for post in incoming for e in validate_post(post, handles)]
    if errors:
        print("X_WATCH_MERGE_FAILED " + " ".join(errors))
        return 1
    path = X_DIR / f"{now.strftime('%Y-%m-%d')}.json"
    posts = {p["url"]: p for p in _load_day(path)}
    added = 0
    for post in incoming:
        post = dict(post, handle=handles[str(post["handle"]).lstrip("@").lower()])
        if post["url"] not in posts:
            added += 1
        posts[post["url"]] = post
    ordered = sorted(posts.values(), key=lambda p: (p["handle"].lower(), p["published"]))
    X_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"posts": ordered}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"X_WATCH_MERGE_OK file={path} added={added} total={len(ordered)}")
    return 0


def cmd_check() -> int:
    handles = _handles()
    errors = []
    for path in sorted(X_DIR.glob("*.json")) if X_DIR.exists() else []:
        if not DAY_RE.match(path.name):
            errors.append(f"bad_filename:{path.name}")
            continue
        seen: set[str] = set()
        for post in _load_day(path):
            errors += [f"{path.name}:{e}" for e in validate_post(post, handles)]
            if post.get("url") in seen:
                errors.append(f"{path.name}:duplicate_url:{post.get('url')}")
            seen.add(post.get("url"))
    if errors:
        print("X_WATCH_CHECK_FAILED " + " ".join(errors))
        return 1
    print("X_WATCH_CHECK_OK")
    return 0


def main(argv: list[str] | None = None, now: datetime | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan")
    merge = sub.add_parser("merge")
    merge.add_argument("--in", dest="in_path", type=Path, required=True)
    sub.add_parser("check")
    args = ap.parse_args(argv)
    now = now or datetime.now(timezone.utc)
    if args.cmd == "plan":
        return cmd_plan(now)
    if args.cmd == "merge":
        return cmd_merge(args.in_path, now)
    return cmd_check()


if __name__ == "__main__":
    sys.exit(main())
