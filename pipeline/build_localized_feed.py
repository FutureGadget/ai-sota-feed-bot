#!/usr/bin/env python3
"""Build the localized live feed snapshot."""

import argparse
import json
import subprocess
import sys
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import google_translate

ROOT = Path(__file__).resolve().parent.parent

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

def _fetch_english_feed(label: str, limit: int) -> dict[str, Any]:
    js_code = f"""
import handler from './api/feed.js';
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
const req = {{ query: {{ label: '{label}', limit: '{limit}', from: w.from, to: w.to }} }};
let out = '';
const res = {{
  status: (code) => ({{
    json: (data) => {{ console.log(JSON.stringify(data)); }}
  }}),
  setHeader: () => {{}}
}};
handler(req, res).catch(console.error);
"""
    cmd = ["node", "-e", js_code]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True)
    return json.loads(res.stdout)


def _translate_items_batch(
    items: list[dict[str, Any]], locale: str, api_key: str
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
        translated = google_translate.translate_texts(texts, locale, api_key=api_key)
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
    args = parser.parse_args()
    
    feed_dir = ROOT / "data" / "i18n" / args.locale / "feed"
    feed_dir.mkdir(parents=True, exist_ok=True)
    latest_path = feed_dir / "latest.json"
    status_path = feed_dir / "status.json"
    
    fetch_limit = max(100, args.limit * 2)
    print(f"Fetching English feed (label={args.label}, limit={fetch_limit})...")
    feed = _fetch_english_feed(args.label, fetch_limit)
    all_items = feed.get("items", [])
    if not all_items:
        print("No items in feed!")
        return
        
    target_items = all_items[:args.limit]
    
    # Get deep_run_at or use current time
    run_at_str = feed.get("tier1_blend", {}).get("deep_run_at")
    if not run_at_str:
        run_at_str = all_items[0].get("first_seen") or datetime.now(timezone.utc).isoformat()
    
    existing = {}
    if latest_path.exists():
        try:
            prev = json.loads(latest_path.read_text())
            for it in prev.get("items", []):
                existing[it.get("translation_key")] = it
        except Exception:
            pass
            
    # Classify feed items into fresh or dirty
    dirty_targets = []
    dirty_lookahead = []
    
    for i, it in enumerate(all_items):
        t_key = _translation_key(it)
        s_hash = _source_hash(it)
        is_fresh = t_key in existing and existing[t_key].get("source_hash") == s_hash
        
        if not is_fresh:
            if i < args.limit:
                dirty_targets.append(it)
            else:
                dirty_lookahead.append(it)
                
    if args.dry_run:
        print(f"\nDRY RUN: Found {len(all_items)} total items.")
        print(f"  Dirty targets (top {args.limit}): {len(dirty_targets)}")
        print(f"  Dirty lookahead: {len(dirty_lookahead)}")
        return

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
        }
        status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote status to {status_path.relative_to(ROOT)}")
        return

    # Translate
    results_map = {k: v for k, v in existing.items()}
    newly_translated = {}
    successes = 0
    failures = 0
    target_failures = 0
    
    if to_translate:
        print(f"Translating up to {len(to_translate)} items (budget: {max_translations})...")
        items_to_translate = [it for it, is_target in to_translate]
        try:
            translated_results = _translate_items_batch(items_to_translate, args.locale, api_key)
            for (it, is_target), trans in zip(to_translate, translated_results):
                t_key = _translation_key(it)
                newly_translated[t_key] = trans
                results_map[t_key] = trans
                successes += 1
            print(f" Successfully translated {successes} items.")
        except Exception as e:
            print(f" Batch translation FAILED: {e}")
            failures = len(to_translate)
            target_failures = sum(1 for it, is_target in to_translate if is_target)
    else:
        print("All target and lookahead items are fresh in cache.")

    # Prune translations that are no longer in the wider feed to prevent infinite cache growth
    valid_keys = {_translation_key(it) for it in all_items}
    final_items = [v for k, v in results_map.items() if k in valid_keys]

    # Verify if the visible target feed (top 20) is complete
    missing_targets = []
    for it in target_items:
        t_key = _translation_key(it)
        s_hash = _source_hash(it)
        if t_key not in results_map or results_map[t_key].get("source_hash") != s_hash:
            missing_targets.append(it.get("title"))
            
    is_complete = len(missing_targets) == 0
    now = datetime.now(timezone.utc)
    
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
        "snapshot_id": f"{now.strftime('%Y%m%d-%H%M%S')}-{args.label}-top{args.limit}",
        "source_run_at": run_at_str,
        "translated_at": now.isoformat(),
        "expires_at": (datetime.fromisoformat(run_at_str.replace("Z", "+00:00")) + timedelta(hours=24)).isoformat(),
        "model": "google-translate-v2",
        "review_status": "machine",
        "eligible_label": args.label,
        "selector": {
            "endpoint": "/api/feed",
            "label": args.label,
            "limit": args.limit,
            "days": 7,
            "blend_tier1": True
        },
        "max_items": args.limit,
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
