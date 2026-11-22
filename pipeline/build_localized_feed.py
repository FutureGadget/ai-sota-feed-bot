#!/usr/bin/env python3
"""Build the localized live feed: the per-card store and the /ko/ snapshot.

One ``translator.Job`` per card, each card translated once into the store
(``cards.json``, see ``card_store``). The store covers the cards the English
home's default request returns plus the 7-day top-N set; the snapshot
(``latest.json``, read by the old /ko/ page) is built from the store without
translating again. Spend is metered in USD by the shared ``translator.Ledger``;
when the monthly cap is reached the store keeps what was translated, the
previous snapshot stays frozen, and ``status.json`` says ``budget_paused``.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    from . import card_store, locales, translator
except ImportError:
    import card_store
    import locales
    import translator

# Feed chrome the localized snapshot carries, per locale.
FEED_UI = {
    "ko": {
        "title": "AI SOTA Feed",
        "description": "최신 AI 기술 소식을 한 곳에서 확인하세요.",
        "feed_title": "오늘의 주요 뉴스",
    },
}

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ("title", "summary_1line", "why_it_matters")
MAX_TRANSLATIONS = 60

def _norm_url(url: str | None) -> str:
    s = str(url or "").strip()
    return s[:-1] if s.endswith("/") and len(s) > 1 else s

def _clean_text(v: Any) -> str:
    if not v:
        return ""
    return " ".join(str(v).split())

def _item_key(it: dict[str, Any]) -> str:
    return str(it.get("url") or it.get("title") or "")

def _translation_key(it: dict[str, Any]) -> str:
    url = _norm_url(it.get("url"))
    return url or str(it.get("id") or it.get("title") or "").strip()

def _source_hash(it: dict[str, Any]) -> str:
    also_covered = it.get("also_covered")
    if not isinstance(also_covered, list):
        also_covered = []

    ac_payload = []
    for entry in also_covered:
        if not isinstance(entry, dict):
            continue
        title = _clean_text(entry.get("title"))
        url = _norm_url(entry.get("url"))
        if url or title:
            ac_payload.append({"title": title, "url": url})

    payload = {
        "also_covered": ac_payload,
        "summary_1line": _clean_text(it.get("summary_1line")),
        "title": _clean_text(it.get("title")),
        "why_it_matters": _clean_text(it.get("why_it_matters")),
    }

    j = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(j.encode('utf-8')).hexdigest()

def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

KST = timezone(timedelta(hours=9))
SNAPSHOT_DAYS = 7
# The English home's default view (web/index.html buildFeedUrl): the Brief lens,
# a rolling 24-hour window keyed by feed arrival, up to 200 cards.
HOME_LABEL = "brief"
HOME_LIMIT = 200
HOME_HOURS = 24

_FETCH_JS = """
import { GET } from './api/feed.js';
const url = new URL('http://localhost/api/feed');
for (const [key, value] of Object.entries(JSON.parse(process.env.FEED_PARAMS))) {
  url.searchParams.set(key, value);
}
GET({ url: url.toString() })
  .then((res) => res.json())
  .then((data) => { console.log(JSON.stringify(data)); })
  .catch((err) => { console.error(err); process.exit(1); });
"""


def _kst_window(days: int, now: datetime) -> dict[str, str]:
    """The last ``days`` Seoul calendar days up to the end of today, as /api/feed from/to."""
    today = now.astimezone(KST).replace(hour=0, minute=0, second=0, microsecond=0)

    def fmt(d: datetime) -> str:
        return d.isoformat(timespec="milliseconds")

    start = today - timedelta(days=days - 1)
    end = today.replace(hour=23, minute=59, second=59, microsecond=999000)
    return {"from": fmt(start), "to": fmt(end)}


def snapshot_params(label: str, limit: int, now: datetime) -> dict[str, str]:
    """/api/feed params for the 7-day snapshot selector the /ko/ page requests."""
    return {"label": label, "limit": str(limit), **_kst_window(SNAPSHOT_DAYS, now)}


def home_params(now: datetime) -> dict[str, str]:
    """/api/feed params of the English home's default request."""
    def fmt(d: datetime) -> str:
        return d.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    return {
        "label": HOME_LABEL,
        "limit": str(HOME_LIMIT),
        "window": "arrival",
        "from": fmt(now - timedelta(hours=HOME_HOURS)),
        "to": fmt(now),
    }


def _fetch_english_feed(params: dict[str, str]) -> dict[str, Any]:
    """The English /api/feed response for ``params``, from the repo's own handler."""
    env = {**os.environ, "FEED_PARAMS": json.dumps(params)}
    res = subprocess.run(
        ["node", "-e", _FETCH_JS], cwd=ROOT, env=env, capture_output=True, text=True, check=True
    )
    return json.loads(res.stdout)


def item_job(it: dict[str, Any]) -> translator.Job:
    """The translation job for one feed card: its visible text, with the article excerpt as context."""
    fields = {f: it[f] for f in FIELDS if (it.get(f) or "").strip()}
    for i, entry in enumerate(it.get("also_covered") or []):
        if isinstance(entry, dict) and (entry.get("title") or "").strip():
            fields[f"also_covered_title_{i}"] = entry["title"]
    context = it.get("content_excerpt") or it.get("summary") or ""
    return translator.Job(_translation_key(it), fields, context)


def _card_entry(
    it: dict[str, Any], result: translator.Result, model: str, now: datetime
) -> card_store.CardEntry:
    """The store entry for one freshly translated English card."""
    return {
        "source_hash": _source_hash(it),
        "model": model,
        "translated_at": now.isoformat(),
        "last_seen": now.isoformat(),
        **{f: result.fields.get(f) or it.get(f) or "" for f in FIELDS},
        "also_covered": [
            {"url": entry.get("url"), "title": result.fields.get(f"also_covered_title_{i}", entry.get("title"))}
            for i, entry in enumerate(it.get("also_covered") or [])
        ],
    }


def _seed_store(store: card_store.CardStore, snapshot: dict[str, Any] | None, now: datetime) -> None:
    """First run only: adopt the existing snapshot's cards so they are not paid for twice."""
    for row in (snapshot or {}).get("items", []):
        key = row.get("translation_key")
        if not key or not row.get("source_hash"):
            continue
        store["cards"][key] = {
            "source_hash": row["source_hash"],
            "model": row.get("model") or "",
            "translated_at": snapshot.get("translated_at") or now.isoformat(),
            "last_seen": now.isoformat(),
            **{f: row.get(f) or "" for f in FIELDS},
            "also_covered": row.get("also_covered") or [],
        }


def _snapshot_card(it: dict[str, Any], entry: card_store.CardEntry) -> dict[str, Any]:
    """One snapshot row: a store entry plus what the API needs to render it frozen."""
    card = {
        "translation_key": _translation_key(it),
        "id": it.get("id"),
        "source_hash": entry["source_hash"],
        "model": entry["model"],
        **{f: entry[f] for f in FIELDS},
    }
    if entry["also_covered"]:
        card["also_covered"] = entry["also_covered"]
    # source_meta lets the API render a dated frozen card from the snapshot
    # alone when the feed is paused/stale. Not covered by source_hash, so
    # refreshing it never re-translates an item.
    card["source_meta"] = {
        "url": it.get("url"),
        "source": it.get("source"),
        "published": it.get("published"),
        "type": it.get("type"),
    }
    return card


def _union(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cards from every group in order, each translation key once."""
    seen: set[str] = set()
    out = []
    for group in groups:
        for it in group:
            key = _translation_key(it)
            if key not in seen:
                seen.add(key)
                out.append(it)
    return out


def _next_month_start(now: datetime) -> datetime:
    """First instant of next month, UTC: when the ledger's month rolls over."""
    year, month = (now.year + 1, 1) if now.month == 12 else (now.year, now.month + 1)
    return datetime(year, month, 1, tzinfo=timezone.utc)


def _budget_block(ledger: translator.Ledger, now: datetime) -> dict[str, Any]:
    return {
        "usd_spent": round(ledger.spent, 4),
        "monthly_usd_cap": ledger.monthly_cap,
        "month": now.strftime("%Y-%m"),
    }


def _write_status(path: Path, status: dict[str, Any]) -> None:
    path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote status to {path.relative_to(ROOT)}")




def main(client=None):
    parser = argparse.ArgumentParser(description="Build the localized live feed: the per-card store and the snapshot.")
    parser.add_argument("--locale", default="ko", choices=locales.others(locales.DEFAULT))
    parser.add_argument("--label", default="brief")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    feed_dir = ROOT / "data" / "i18n" / args.locale / "feed"
    feed_dir.mkdir(parents=True, exist_ok=True)
    latest_path = feed_dir / "latest.json"
    status_path = feed_dir / "status.json"
    store_path = card_store.store_path(ROOT, args.locale)

    now = datetime.now(timezone.utc)
    model = translator.model_for("feed")
    ledger = translator.Ledger(ROOT / "data" / "i18n" / "translation_spend.json", now=lambda: now)
    print(f"localized_feed_budget usd_spent={ledger.spent:.4f} cap={ledger.monthly_cap:.2f} month={now:%Y-%m}")

    existing_snapshot = _read_json(latest_path)
    store = card_store.load(store_path, args.locale)
    if not store["cards"]:
        _seed_store(store, existing_snapshot, now)

    fetch_limit = max(100, args.limit * 2)
    print(f"Fetching English feed (label={args.label}, limit={fetch_limit})...")
    feed = _fetch_english_feed(snapshot_params(args.label, fetch_limit, now))
    all_items = feed.get("items", [])
    if not all_items:
        print("No items in feed!")
        return

    print(f"Fetching the English home's default feed (label={HOME_LABEL}, limit={HOME_LIMIT})...")
    home_items = _fetch_english_feed(home_params(now)).get("items", [])

    target_items = all_items[: args.limit]
    # The snapshot's freshness clock is the newest feed run it was built from
    # (/api/feed returns runs newest first), not when its top card was first seen.
    runs = feed.get("runs") or []
    run_at_str = (runs[0].get("run_at") if runs and isinstance(runs[0], dict) else None) or now.isoformat()

    # Translate the snapshot's top N first (the /ko/ page needs them), then the
    # home's cards, then the snapshot's lookahead.
    wanted = _union(target_items, home_items, all_items[args.limit :])
    dirty = [
        it for it in wanted
        if not card_store.is_fresh(store["cards"].get(_translation_key(it)), _source_hash(it), model)
    ]
    to_translate = dirty[:MAX_TRANSLATIONS]

    if args.dry_run:
        print(f"\nDRY RUN: {len(wanted)} cards to keep translated.")
        print(f"  Snapshot set: {len(all_items)} (top {args.limit} + lookahead)")
        print(f"  English home default feed: {len(home_items)}")
        print(f"  Already translated: {len(wanted) - len(dirty)}")
        print(f"  Would translate: {len(to_translate)} of {len(dirty)} untranslated (max {MAX_TRANSLATIONS} per run)")
        return

    # Translate one card per call, so a card that fails does not discard the others.
    translated = 0
    budget_hit = False

    if to_translate:
        print(f"Translating up to {len(to_translate)} items (max {MAX_TRANSLATIONS})...")
        try:
            client = client or translator.make_client()
        except Exception as exc:
            print(f" Cannot create the Anthropic client: {exc}", file=sys.stderr)
            to_translate = []
        for it in to_translate:
            try:
                (result,) = translator.translate(
                    [item_job(it)], args.locale, "feed", client=client, ledger=ledger
                )
            except translator.BudgetExceeded as exc:
                print(f" Monthly cap reached: {exc}", file=sys.stderr)
                budget_hit = True
                break
            except translator.TranslationError as exc:
                print(f" Translation FAILED: {exc}", file=sys.stderr)
                continue
            except Exception as exc:
                print(f" Translation FAILED, stopping: {exc}", file=sys.stderr)
                break
            store["cards"][_translation_key(it)] = _card_entry(it, result, model, now)
            translated += 1
        print(f" Translated {translated} items.")
    else:
        print("All wanted cards are already translated.")

    for it in wanted:
        entry = store["cards"].get(_translation_key(it))
        if entry:
            entry["last_seen"] = now.isoformat()
    pruned = card_store.prune(store, now)
    card_store.save(store_path, store, now)
    print(f"Wrote {len(store['cards'])} cards to {store_path.relative_to(ROOT)} (pruned {pruned})")

    # Verify if the visible target feed (top N) is complete
    missing_targets = []
    for it in target_items:
        entry = store["cards"].get(_translation_key(it))
        if not entry or entry["source_hash"] != _source_hash(it):
            missing_targets.append(it.get("title"))

    if budget_hit and missing_targets:
        # Keep serving the frozen snapshot; the cap resets with the ledger month.
        resumes_at = _next_month_start(now).isoformat()
        snapshot = existing_snapshot or {}
        status = {
            "locale": args.locale,
            "surface": "feed",
            "status": "budget_paused",
            "reason": "monthly_cap",
            "resumes_at": resumes_at,
            "budget": _budget_block(ledger, now),
            "source_run_at": snapshot.get("source_run_at") or run_at_str,
            "translated_at": snapshot.get("translated_at"),
            "expires_at": snapshot.get("expires_at"),
            "eligible_count": len(target_items),
            "translated_count": snapshot.get("translated_item_count", 0),
            "missing_count": len(target_items),
        }
        _write_status(status_path, status)
        print(f"localized_feed_budget_paused reason=monthly_cap resumes_at={resumes_at}")
        return

    # The snapshot is built from the store: every card of the fetched feed it holds.
    final_items = [
        _snapshot_card(it, store["cards"][_translation_key(it)])
        for it in _union(all_items)
        if _translation_key(it) in store["cards"]
    ]

    is_complete = len(missing_targets) == 0

    ui = FEED_UI.get(args.locale, {})

    snapshot = {
        "locale": args.locale,
        "surface": "feed",
        "source_path": "/",
        "target_path": locales.path(args.locale, "/"),
        "snapshot_id": f"{now.strftime('%Y%m%d-%H%M%S')}-{args.label}-top{args.limit}",
        "source_run_at": run_at_str,
        "translated_at": now.isoformat(),
        "expires_at": (datetime.fromisoformat(run_at_str.replace("Z", "+00:00")) + timedelta(hours=24)).isoformat(),
        "model": model,
        "review_status": "machine",
        "eligible_label": args.label,
        "selector": {
            "endpoint": "/api/feed",
            "label": args.label,
            "limit": args.limit,
            "days": SNAPSHOT_DAYS
        },
        "max_items": args.limit,
        "source_item_count": len(target_items),
        "translated_item_count": len(target_items) - len(missing_targets),
        "is_complete": is_complete,
        # Ranked top-N keys at build time: the frozen-render order once the
        # snapshot outlives the live feed (items carries lookahead cache too).
        "target_keys": [_translation_key(it) for it in target_items],
        "items": final_items,
        "ui": ui
    }

    status = {
        "locale": args.locale,
        "surface": "feed",
        "status": "current" if is_complete else "incomplete",
        "reason": None if is_complete else f"{len(missing_targets)}_targets_missing",
        "budget": _budget_block(ledger, now),
        "source_run_at": snapshot["source_run_at"],
        "translated_at": snapshot["translated_at"],
        "expires_at": snapshot["expires_at"],
        "eligible_count": len(target_items),
        "translated_count": len(target_items) - len(missing_targets),
        "missing_count": len(missing_targets)
    }

    if is_complete or not latest_path.exists():
        latest_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote snapshot to {latest_path.relative_to(ROOT)}")

    _write_status(status_path, status)

    if not is_complete:
        print(f"ERROR: Missing translations for {len(missing_targets)} target items: {missing_targets}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
