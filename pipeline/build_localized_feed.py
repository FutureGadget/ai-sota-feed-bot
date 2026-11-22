#!/usr/bin/env python3
"""Build the localized live feed snapshot.

One ``translator.Job`` per card. Spend is metered in USD by the shared
``translator.Ledger``; when the monthly cap is reached the previous snapshot
stays frozen and ``status.json`` says ``budget_paused``.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    from . import locales, translator
except ImportError:
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
MAX_TRANSLATIONS = 20

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

def _translation_map(snapshot: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not snapshot:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for it in snapshot.get("items", []):
        key = it.get("translation_key")
        if key:
            out[key] = it
    return out

def _classify_dirty(
    all_items: list[dict[str, Any]], existing: dict[str, dict[str, Any]], limit: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    dirty_targets = []
    dirty_lookahead = []
    for i, it in enumerate(all_items):
        t_key = _translation_key(it)
        s_hash = _source_hash(it)
        card = existing.get(t_key) or {}
        # A card is fresh only if the current feed model translated this exact
        # source; cards from an older translator or model are redone.
        is_fresh = card.get("source_hash") == s_hash and card.get("model") == translator.model_for("feed")
        if not is_fresh:
            if i < limit:
                dirty_targets.append(it)
            else:
                dirty_lookahead.append(it)
    return dirty_targets, dirty_lookahead

def _fetch_english_feed(label: str, limit: int) -> dict[str, Any]:
    js_code = f"""
import {{ GET }} from './api/feed.js';
function kstWindow(days) {{
  const now = new Date();
  const kstNow = new Date(now.toLocaleString('en-US', {{ timeZone: 'Asia/Seoul' }}));
  const end = new Date(kstNow.getFullYear(), kstNow.getMonth(), kstNow.getDate(), 23, 59, 59, 999);
  const start = new Date(kstNow.getFullYear(), kstNow.getMonth(), kstNow.getDate() - (days - 1), 0, 0, 0, 0);
  const offset = '+09:00';
  const fmt = (d) => {{
    const pad = (n, w = 2) => String(n).padStart(w, '0');
    return `${{d.getFullYear()}}-${{pad(d.getMonth() + 1)}}-${{pad(d.getDate())}}T${{pad(d.getHours())}}:${{pad(d.getMinutes())}}:${{pad(d.getSeconds())}}.${{pad(d.getMilliseconds(), 3)}}${{offset}}`;
  }};
  return {{ from: fmt(start), to: fmt(end) }};
}}
const w = kstWindow(7);
const url = new URL('http://localhost/api/feed');
url.searchParams.set('label', '{label}');
url.searchParams.set('limit', '{limit}');
url.searchParams.set('from', w.from);
url.searchParams.set('to', w.to);
const req = {{ url: url.toString() }};
GET(req)
  .then(res => res.json())
  .then(data => {{ console.log(JSON.stringify(data)); }})
  .catch(console.error);
"""
    cmd = ["node", "-e", js_code]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True)
    return json.loads(res.stdout)


def item_job(it: dict[str, Any]) -> translator.Job:
    """The translation job for one feed card: its visible text, with the article excerpt as context."""
    fields = {f: it[f] for f in FIELDS if (it.get(f) or "").strip()}
    for i, entry in enumerate(it.get("also_covered") or []):
        if isinstance(entry, dict) and (entry.get("title") or "").strip():
            fields[f"also_covered_title_{i}"] = entry["title"]
    context = it.get("content_excerpt") or it.get("summary") or ""
    return translator.Job(_translation_key(it), fields, context)


def _localized_card(it: dict[str, Any], result: translator.Result) -> dict[str, Any]:
    card = {
        "translation_key": _translation_key(it),
        "id": it.get("id"),
        "source_hash": _source_hash(it),
        "model": translator.model_for("feed"),
    }
    for f in FIELDS:
        card[f] = result.fields.get(f) or it.get(f)
    if it.get("also_covered"):
        card["also_covered"] = [
            {"url": entry.get("url"), "title": result.fields.get(f"also_covered_title_{i}", entry.get("title"))}
            for i, entry in enumerate(it["also_covered"])
        ]
    return card


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
    parser = argparse.ArgumentParser(description="Build the localized live feed snapshot.")
    parser.add_argument("--locale", default="ko", choices=locales.others(locales.DEFAULT))
    parser.add_argument("--label", default="brief")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    feed_dir = ROOT / "data" / "i18n" / args.locale / "feed"
    feed_dir.mkdir(parents=True, exist_ok=True)
    latest_path = feed_dir / "latest.json"
    status_path = feed_dir / "status.json"

    now = datetime.now(timezone.utc)
    ledger = translator.Ledger(ROOT / "data" / "i18n" / "translation_spend.json", now=lambda: now)
    print(f"localized_feed_budget usd_spent={ledger.spent:.4f} cap={ledger.monthly_cap:.2f} month={now:%Y-%m}")

    existing_snapshot = _read_json(latest_path)

    fetch_limit = max(100, args.limit * 2)
    print(f"Fetching English feed (label={args.label}, limit={fetch_limit})...")
    feed = _fetch_english_feed(args.label, fetch_limit)
    all_items = feed.get("items", [])
    if not all_items:
        print("No items in feed!")
        return

    target_items = all_items[: args.limit]

    # Anchor the snapshot to the newest ranked item's arrival time.
    run_at_str = all_items[0].get("first_seen") or datetime.now(timezone.utc).isoformat()

    existing = _translation_map(existing_snapshot)

    # Classify feed items into fresh or dirty
    dirty_targets, dirty_lookahead = _classify_dirty(all_items, existing, args.limit)
    to_translate = (dirty_targets + dirty_lookahead)[:MAX_TRANSLATIONS]

    if args.dry_run:
        print(f"\nDRY RUN: Found {len(all_items)} total items.")
        print(f"  Dirty targets (top {args.limit}): {len(dirty_targets)}")
        print(f"  Dirty lookahead: {len(dirty_lookahead)}")
        print(f"  Would translate: {len(to_translate)}")
        return

    # Translate one card per call, so a card that fails does not discard the others.
    results_map = dict(existing)
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
            results_map[_translation_key(it)] = _localized_card(it, result)
            translated += 1
        print(f" Translated {translated} items.")
    else:
        print("All target and lookahead items are fresh in cache.")

    # Verify if the visible target feed (top N) is complete
    missing_targets = []
    for it in target_items:
        t_key = _translation_key(it)
        s_hash = _source_hash(it)
        if t_key not in results_map or results_map[t_key].get("source_hash") != s_hash:
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

    # Prune translations that are no longer in the wider feed to prevent infinite cache growth
    valid_keys = {_translation_key(it) for it in all_items}
    # source_meta lets the API render a dated frozen card from the snapshot
    # alone when the feed is paused/stale. Not covered by source_hash, so
    # refreshing it never re-translates an item.
    meta_by_key = {
        _translation_key(it): {
            "url": it.get("url"),
            "source": it.get("source"),
            "published": it.get("published"),
            "type": it.get("type"),
        }
        for it in all_items
    }
    final_items = [
        {**v, "source_meta": meta_by_key[k]} if k in meta_by_key else dict(v)
        for k, v in results_map.items()
        if k in valid_keys
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
        "model": translator.model_for("feed"),
        "review_status": "machine",
        "eligible_label": args.label,
        "selector": {
            "endpoint": "/api/feed",
            "label": args.label,
            "limit": args.limit,
            "days": 7
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
