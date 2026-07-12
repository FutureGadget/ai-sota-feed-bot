#!/usr/bin/env python3
"""Build the localized live feed snapshot."""

import argparse
import json
import os
import subprocess
import sys
import hashlib
from calendar import monthrange
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import google_translate

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Budget governor constants
# ---------------------------------------------------------------------------

DEFAULT_MONTHLY_CAP = 500_000
DEFAULT_CONSERVE_MIN_AGE_HOURS = 6.0
PAUSE_FLOOR_FRACTION = 0.02
ECONOMY_OVER_PACE = 0.15
ECONOMY_LIMIT = 10
LEDGER_HISTORY_CAP = 200
PACIFIC_TZ = ZoneInfo("America/Los_Angeles")

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
        is_fresh = t_key in existing and existing[t_key].get("source_hash") == s_hash
        if not is_fresh:
            if i < limit:
                dirty_targets.append(it)
            else:
                dirty_lookahead.append(it)
    return dirty_targets, dirty_lookahead

def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None

def _hours_since(iso_str: Any, now: datetime) -> float | None:
    dt = _parse_iso(iso_str)
    if dt is None:
        return None
    return (now - dt).total_seconds() / 3600.0


# ---------------------------------------------------------------------------
# Ledger: data/i18n/<locale>/feed/budget.json
# ---------------------------------------------------------------------------

def _monthly_cap_from_env() -> int:
    raw = os.environ.get("GOOGLE_TRANSLATE_MONTHLY_CHAR_CAP")
    if not raw:
        return DEFAULT_MONTHLY_CAP
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_MONTHLY_CAP

def _governor_enabled() -> bool:
    return os.environ.get("LOCALIZED_FEED_BUDGET_GOVERNOR", "1") != "0"

def _conserve_min_age_hours() -> float:
    raw = os.environ.get("LOCALIZED_FEED_CONSERVE_MIN_AGE_HOURS")
    if not raw:
        return DEFAULT_CONSERVE_MIN_AGE_HOURS
    try:
        return max(0.0, float(raw))
    except ValueError:
        return DEFAULT_CONSERVE_MIN_AGE_HOURS

def _current_month(now: datetime) -> str:
    return now.strftime("%Y-%m")

def load_ledger(path: Path, monthly_cap: int, now: datetime) -> dict[str, Any]:
    """Load the ledger, applying month rollover if the stored month is stale."""
    ledger = _read_json(path) or {}
    month = _current_month(now)
    if ledger.get("month") != month:
        prior_history = ledger.get("history")
        ledger = {
            "month": month,
            "chars_used": 0,
            "history": prior_history if isinstance(prior_history, list) else [],
        }
    ledger.setdefault("chars_used", 0)
    ledger.setdefault("history", [])
    ledger["monthly_cap"] = monthly_cap
    return ledger

def save_ledger(path: Path, ledger: dict[str, Any], now: datetime) -> None:
    ledger["updated_at"] = now.isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def record_usage(ledger: dict[str, Any], chars: int, run_id: str, now: datetime) -> None:
    if chars <= 0:
        return
    ledger["chars_used"] = int(ledger.get("chars_used", 0)) + int(chars)
    history = ledger.setdefault("history", [])
    history.append({"at": now.isoformat(), "chars": int(chars), "run": run_id})
    if len(history) > LEDGER_HISTORY_CAP:
        del history[: len(history) - LEDGER_HISTORY_CAP]

def seed_ledger(ledger: dict[str, Any], chars: int, note: str | None, now: datetime) -> None:
    ledger["chars_used"] = max(0, int(chars))
    ledger["seeded_from"] = note or f"seed {now.strftime('%Y-%m-%d')}"

def _budget_block(ledger: dict[str, Any]) -> dict[str, Any]:
    return {
        "chars_used": int(ledger.get("chars_used") or 0),
        "monthly_cap": int(ledger.get("monthly_cap") or DEFAULT_MONTHLY_CAP),
        "month": ledger.get("month"),
    }


# ---------------------------------------------------------------------------
# Governor: mode selection
# ---------------------------------------------------------------------------

def _next_month_utc(now: datetime) -> datetime:
    year, month = now.year, now.month
    if month == 12:
        return datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    return datetime(year, month + 1, 1, tzinfo=timezone.utc)

def _next_pacific_midnight(now: datetime) -> datetime:
    now_pt = now.astimezone(PACIFIC_TZ)
    today_midnight = now_pt.replace(hour=0, minute=0, second=0, microsecond=0)
    next_midnight = today_midnight + timedelta(days=1)
    return next_midnight.astimezone(timezone.utc)

def select_mode(
    ledger: dict[str, Any],
    now: datetime,
    prev_status: dict[str, Any] | None,
    governor_enabled: bool,
    conserve_min_age_hours: float,
) -> tuple[str, str | None, str | None]:
    """Pick the governor mode. Returns (mode, pause_reason, resumes_at_iso)."""
    if not governor_enabled:
        return "normal", None, None

    monthly_cap = max(1, int(ledger.get("monthly_cap") or DEFAULT_MONTHLY_CAP))
    chars_used = int(ledger.get("chars_used") or 0)
    remaining_fraction = (monthly_cap - chars_used) / monthly_cap

    if remaining_fraction < PAUSE_FLOOR_FRACTION:
        return "paused", "monthly_budget", _next_month_utc(now).isoformat()

    prev_status = prev_status or {}
    prev_resumes_at = _parse_iso(prev_status.get("resumes_at"))
    if (
        prev_status.get("status") == "budget_paused"
        and prev_status.get("reason") == "provider_daily_cap"
        and prev_resumes_at is not None
        and now < prev_resumes_at
    ):
        return "paused", "provider_daily_cap", prev_status.get("resumes_at")

    days_in_month = monthrange(now.year, now.month)[1]
    month_fraction_elapsed = now.day / days_in_month
    budget_fraction_used = chars_used / monthly_cap

    if budget_fraction_used > month_fraction_elapsed + ECONOMY_OVER_PACE:
        return "economy", None, None
    if budget_fraction_used > month_fraction_elapsed:
        return "conserve", None, None
    return "normal", None, None


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


def _translate_items_batch(
    items: list[dict[str, Any]], locale: str, api_key: str, *, stats: dict | None = None
) -> list[dict[str, Any]]:
    """Translate all items in a single batched API call."""
    # 1. Collect all translatable strings with their (item_idx, field) addresses
    entries: list[tuple[int, str, int | None, str]] = []  # (item_idx, field, ac_idx, text)
    for idx, it in enumerate(items):
        for field in ("title", "summary_1line", "why_it_matters"):
            text = it.get(field) or ""
            if text.strip():
                entries.append((idx, field, None, text))
        for ac_idx, entry in enumerate(it.get("also_covered") or []):
            title = entry.get("title") or ""
            if title.strip():
                entries.append((idx, "also_covered_title", ac_idx, title))

    # 2. Batch translate all strings at once
    texts = [e[3] for e in entries]
    if texts:
        translated = google_translate.translate_texts(texts, locale, api_key=api_key, stats=stats)
    else:
        translated = []

    # 3. Build translation map: item_idx -> translated fields
    trans_map: dict[int, dict[str, Any]] = {}
    for (item_idx, field, ac_idx, _orig), trans_text in zip(entries, translated):
        if item_idx not in trans_map:
            trans_map[item_idx] = {"ac": {}}
        if field == "also_covered_title":
            trans_map[item_idx]["ac"][ac_idx] = trans_text
        else:
            trans_map[item_idx][field] = trans_text

    # 4. Assemble results
    results = []
    for idx, it in enumerate(items):
        tm = trans_map.get(idx, {})
        res = {
            "translation_key": _translation_key(it),
            "id": it.get("id"),
            "source_hash": _source_hash(it),
            "title": tm.get("title") or it.get("title"),
            "summary_1line": tm.get("summary_1line") or it.get("summary_1line"),
            "why_it_matters": tm.get("why_it_matters") or it.get("why_it_matters"),
        }
        if it.get("also_covered"):
            merged_ac = []
            ac_map = tm.get("ac", {})
            for ac_i, entry in enumerate(it["also_covered"]):
                t_title = ac_map.get(ac_i, entry.get("title"))
                merged_ac.append({"url": entry.get("url"), "title": t_title})
            res["also_covered"] = merged_ac
        results.append(res)
    return results

def main():
    parser = argparse.ArgumentParser(description="Build the localized live feed snapshot.")
    parser.add_argument("--locale", default="ko")
    parser.add_argument("--label", default="brief")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--seed-chars", type=int, default=None,
        help="One-off: overwrite this month's ledger chars_used (from Cloud Console month-to-date) and exit.",
    )
    parser.add_argument(
        "--seed-note", default=None,
        help="Note recorded alongside --seed-chars, e.g. 'console 2026-07-12'.",
    )
    args = parser.parse_args()

    feed_dir = ROOT / "data" / "i18n" / args.locale / "feed"
    feed_dir.mkdir(parents=True, exist_ok=True)
    latest_path = feed_dir / "latest.json"
    status_path = feed_dir / "status.json"
    budget_path = feed_dir / "budget.json"

    now = datetime.now(timezone.utc)
    monthly_cap = _monthly_cap_from_env()

    # Governor bookkeeping failures must never block translation: fail open to
    # "normal" mode (today's behavior) rather than crash or wrongly pause,
    # mirroring the missing-credentials graceful-degradation path below.
    governor_ok = True
    try:
        ledger = load_ledger(budget_path, monthly_cap, now)
    except Exception as exc:
        print(f"Budget ledger load failed, governor disabled for this run: {exc}", file=sys.stderr)
        ledger = {"month": _current_month(now), "chars_used": 0, "monthly_cap": monthly_cap, "history": []}
        governor_ok = False

    if args.seed_chars is not None:
        seed_ledger(ledger, args.seed_chars, args.seed_note, now)
        save_ledger(budget_path, ledger, now)
        print(f"Seeded ledger: chars_used={ledger['chars_used']} month={ledger['month']} seeded_from={ledger.get('seeded_from')!r}")
        return

    prev_status = _read_json(status_path) or {}
    conserve_min_age_hours = _conserve_min_age_hours()

    try:
        mode, pause_reason, resumes_at = select_mode(
            ledger, now, prev_status, _governor_enabled() and governor_ok, conserve_min_age_hours
        )
    except Exception as exc:
        print(f"Governor mode selection failed, falling back to normal mode: {exc}", file=sys.stderr)
        mode, pause_reason, resumes_at = "normal", None, None

    print(
        f"localized_feed_budget mode={mode} chars_used={ledger.get('chars_used', 0)} "
        f"cap={ledger.get('monthly_cap')} month={ledger.get('month')}"
    )

    existing_snapshot = _read_json(latest_path)

    if args.dry_run:
        print(f"\nDRY RUN: mode={mode}" + (f" pause_reason={pause_reason} resumes_at={resumes_at}" if mode == "paused" else ""))
        if mode == "paused":
            print("Would skip translation (paused) and keep the previous snapshot.")
            return
        effective_limit = ECONOMY_LIMIT if mode == "economy" else args.limit
        if mode in ("conserve", "economy") and existing_snapshot:
            age_hours = _hours_since(existing_snapshot.get("source_run_at"), now)
            if age_hours is not None and age_hours < conserve_min_age_hours:
                print(f"Would skip translation (conserve cadence, snapshot age {age_hours:.2f}h < {conserve_min_age_hours}h).")
                return
        fetch_limit = max(100, effective_limit * 2)
        print(f"Fetching English feed (label={args.label}, limit={fetch_limit})...")
        feed = _fetch_english_feed(args.label, fetch_limit)
        all_items = feed.get("items", [])
        if not all_items:
            print("No items in feed!")
            return
        existing = _translation_map(existing_snapshot)
        dirty_targets, dirty_lookahead = _classify_dirty(all_items, existing, effective_limit)
        print(f"\nDRY RUN: Found {len(all_items)} total items.")
        print(f"  Effective limit: {effective_limit} (mode={mode})")
        print(f"  Dirty targets (top {effective_limit}): {len(dirty_targets)}")
        print(f"  Dirty lookahead: {len(dirty_lookahead)}")
        return

    if mode == "paused":
        reason = pause_reason or "monthly_budget"
        status = {
            "locale": args.locale,
            "surface": "feed",
            "status": "budget_paused",
            "reason": reason,
            "resumes_at": resumes_at,
            "mode": "paused",
            "budget": _budget_block(ledger),
            "source_run_at": (existing_snapshot or {}).get("source_run_at") or prev_status.get("source_run_at"),
            "translated_at": (existing_snapshot or {}).get("translated_at") or prev_status.get("translated_at"),
            "expires_at": (existing_snapshot or {}).get("expires_at") or prev_status.get("expires_at"),
            "eligible_count": (existing_snapshot or {}).get("source_item_count", prev_status.get("eligible_count")),
            "translated_count": (existing_snapshot or {}).get("translated_item_count", prev_status.get("translated_count")),
            "missing_count": 0,
        }
        save_ledger(budget_path, ledger, now)
        status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote status to {status_path.relative_to(ROOT)}")
        print(f"localized_feed_budget_paused reason={reason} resumes_at={resumes_at}")
        return

    effective_limit = ECONOMY_LIMIT if mode == "economy" else args.limit

    if mode in ("conserve", "economy") and existing_snapshot:
        age_hours = _hours_since(existing_snapshot.get("source_run_at"), now)
        if age_hours is not None and age_hours < conserve_min_age_hours:
            status = {
                "locale": args.locale,
                "surface": "feed",
                "status": "current",
                "reason": None,
                "mode": mode,
                "budget": _budget_block(ledger),
                "source_run_at": existing_snapshot.get("source_run_at"),
                "translated_at": existing_snapshot.get("translated_at"),
                "expires_at": existing_snapshot.get("expires_at"),
                "eligible_count": existing_snapshot.get("source_item_count", len(existing_snapshot.get("items", []))),
                "translated_count": existing_snapshot.get("translated_item_count", len(existing_snapshot.get("items", []))),
                "missing_count": 0,
            }
            save_ledger(budget_path, ledger, now)
            status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Wrote status to {status_path.relative_to(ROOT)}")
            print(f"localized_feed_budget mode={mode} skip=conserve_cadence age_hours={age_hours:.2f}")
            return

    fetch_limit = max(100, effective_limit * 2)
    print(f"Fetching English feed (label={args.label}, limit={fetch_limit})...")
    feed = _fetch_english_feed(args.label, fetch_limit)
    all_items = feed.get("items", [])
    if not all_items:
        print("No items in feed!")
        return

    target_items = all_items[:effective_limit]

    # Get deep_run_at or use current time
    run_at_str = feed.get("tier1_blend", {}).get("deep_run_at")
    if not run_at_str:
        run_at_str = all_items[0].get("first_seen") or datetime.now(timezone.utc).isoformat()

    existing = _translation_map(existing_snapshot)

    # Classify feed items into fresh or dirty
    dirty_targets, dirty_lookahead = _classify_dirty(all_items, existing, effective_limit)

    # Check Google Translate credentials if we actually need to translate anything
    to_translate = []
    max_translations = 20

    for it in dirty_targets:
        if len(to_translate) < max_translations:
            to_translate.append((it, True))  # (item, is_target)

    for it in dirty_lookahead:
        if len(to_translate) < max_translations:
            to_translate.append((it, False))  # (item, is_target)

    api_key = google_translate.get_api_key()
    if to_translate and not api_key:
        print("GOOGLE_TRANSLATE_API_KEY not set — skipping translation.", file=sys.stderr)
        status = {
            "locale": args.locale,
            "surface": "feed",
            "status": "localized_feed_missing_credentials",
            "reason": "GOOGLE_TRANSLATE_API_KEY not set",
            "mode": mode,
            "budget": _budget_block(ledger),
        }
        save_ledger(budget_path, ledger, now)
        status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote status to {status_path.relative_to(ROOT)}")
        return

    # Translate
    results_map = {k: v for k, v in existing.items()}
    newly_translated = {}
    successes = 0
    failures = 0
    target_failures = 0
    stats: dict[str, int] = {"chars_sent": 0}

    if to_translate:
        print(f"Translating up to {len(to_translate)} items (budget: {max_translations})...")
        items_to_translate = [it for it, is_target in to_translate]
        try:
            translated_results = _translate_items_batch(items_to_translate, args.locale, api_key, stats=stats)
            for (it, is_target), trans in zip(to_translate, translated_results):
                t_key = _translation_key(it)
                newly_translated[t_key] = trans
                results_map[t_key] = trans
                successes += 1
            print(f" Successfully translated {successes} items.")
        except google_translate.QuotaExceededError as exc:
            if stats.get("chars_sent"):
                record_usage(ledger, stats["chars_sent"], f"{now.strftime('%Y%m%d-%H%M%S')}-quota", now)
            monthly_cap_val = max(1, int(ledger.get("monthly_cap") or DEFAULT_MONTHLY_CAP))
            chars_used_val = int(ledger.get("chars_used") or 0)
            remaining_fraction = (monthly_cap_val - chars_used_val) / monthly_cap_val
            if remaining_fraction < PAUSE_FLOOR_FRACTION:
                pause_reason = "monthly_budget"
                pause_resumes_at = _next_month_utc(now).isoformat()
            else:
                pause_reason = "provider_daily_cap"
                pause_resumes_at = _next_pacific_midnight(now).isoformat()
            status = {
                "locale": args.locale,
                "surface": "feed",
                "status": "budget_paused",
                "reason": pause_reason,
                "resumes_at": pause_resumes_at,
                "mode": "paused",
                "budget": _budget_block(ledger),
                "source_run_at": (existing_snapshot or {}).get("source_run_at") or run_at_str,
                "translated_at": (existing_snapshot or {}).get("translated_at"),
                "expires_at": (existing_snapshot or {}).get("expires_at"),
                "eligible_count": len(target_items),
                "translated_count": (existing_snapshot or {}).get("translated_item_count", 0),
                "missing_count": len(target_items),
            }
            save_ledger(budget_path, ledger, now)
            status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Wrote status to {status_path.relative_to(ROOT)}")
            print(f"localized_feed_budget_paused reason={pause_reason} resumes_at={pause_resumes_at}")
            print(f"Quota exceeded during translation: {exc}", file=sys.stderr)
            return
        except Exception as e:
            print(f" Batch translation FAILED: {e}")
            failures = len(to_translate)
            target_failures = sum(1 for it, is_target in to_translate if is_target)
    else:
        print("All target and lookahead items are fresh in cache.")

    if stats.get("chars_sent"):
        record_usage(ledger, stats["chars_sent"], f"{now.strftime('%Y%m%d-%H%M%S')}-{args.label}", now)
    save_ledger(budget_path, ledger, now)

    # Prune translations that are no longer in the wider feed to prevent infinite cache growth
    valid_keys = {_translation_key(it) for it in all_items}
    final_items = [v for k, v in results_map.items() if k in valid_keys]

    # Verify if the visible target feed (top N) is complete
    missing_targets = []
    for it in target_items:
        t_key = _translation_key(it)
        s_hash = _source_hash(it)
        if t_key not in results_map or results_map[t_key].get("source_hash") != s_hash:
            missing_targets.append(it.get("title"))

    is_complete = len(missing_targets) == 0

    # UI defaults for ko
    ui = {}
    if args.locale == "ko":
        ui = {
            "title": "AI SOTA Feed",
            "description": "최신 AI 기술 소식을 한 곳에서 확인하세요.",
            "feed_title": "오늘의 주요 뉴스"
        }

    snapshot = {
        "locale": args.locale,
        "surface": "feed",
        "source_path": "/",
        "target_path": f"/{args.locale}/",
        "snapshot_id": f"{now.strftime('%Y%m%d-%H%M%S')}-{args.label}-top{effective_limit}",
        "source_run_at": run_at_str,
        "translated_at": now.isoformat(),
        "expires_at": (datetime.fromisoformat(run_at_str.replace("Z", "+00:00")) + timedelta(hours=24)).isoformat(),
        "model": "google-translate-v2",
        "review_status": "machine",
        "eligible_label": args.label,
        "selector": {
            "endpoint": "/api/feed",
            "label": args.label,
            "limit": effective_limit,
            "days": 7,
            "blend_tier1": True
        },
        "max_items": effective_limit,
        "source_item_count": len(target_items),
        "translated_item_count": len(target_items) - len(missing_targets),
        "is_complete": is_complete,
        "items": final_items,
        "ui": ui
    }

    status = {
        "locale": args.locale,
        "surface": "feed",
        "status": "current" if is_complete else "incomplete",
        "reason": None if is_complete else f"{len(missing_targets)}_targets_missing",
        "mode": mode,
        "budget": _budget_block(ledger),
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

    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote status to {status_path.relative_to(ROOT)}")

    if not is_complete:
        print(f"ERROR: Missing translations for {len(missing_targets)} target items: {missing_targets}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
