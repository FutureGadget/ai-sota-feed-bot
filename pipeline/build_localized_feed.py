#!/usr/bin/env python3
"""Build the localized live feed snapshot."""

import argparse
import json
import subprocess
import sys
import hashlib
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

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

def _chat_completion(base_url, model, messages, temperature=0.3, timeout=300):
    import urllib.request
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 4096,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        raise ConnectionError(f"LM Studio API Error (HTTP {exc.code}): {err_body}") from exc
    except Exception as exc:
        raise ConnectionError(f"Cannot reach LM Studio at {base_url}. Error: {exc}") from exc
    return body["choices"][0]["message"]["content"]

def _repair_unescaped_quotes(text: str) -> str:
    """Escape unescaped double quotes inside JSON string values."""
    chars = list(text)
    n = len(chars)
    result = []
    inside_string = False
    
    i = 0
    while i < n:
        c = chars[i]
        
        if c == '"':
            # Check if this quote is escaped
            is_escaped = False
            k = i - 1
            while k >= 0 and chars[k] == '\\':
                is_escaped = not is_escaped
                k -= 1
                
            if is_escaped:
                result.append(c)
                i += 1
                continue
                
            if not inside_string:
                inside_string = True
                result.append(c)
                i += 1
            else:
                # Look ahead for next non-whitespace char
                next_non_ws = None
                j = i + 1
                while j < n:
                    if chars[j] not in (' ', '\t', '\n', '\r'):
                        next_non_ws = chars[j]
                        break
                    j += 1
                
                # If followed by a JSON structural separator, it's closing the string
                if next_non_ws in (',', '}', ']', ':'):
                    inside_string = False
                    result.append(c)
                else:
                    # Escape it
                    result.append('\\')
                    result.append('"')
                i += 1
        else:
            result.append(c)
            i += 1
            
    return "".join(result)


def _translate_item(it: dict[str, Any], locale: str, base_url: str, model: str) -> dict[str, Any]:
    source_json = {
        "title": it.get("title"),
        "summary_1line": it.get("summary_1line"),
        "why_it_matters": it.get("why_it_matters"),
    }
    if it.get("also_covered"):
        source_json["also_covered"] = it["also_covered"]

    prompt = f"""Translate these feed item fields from English to {locale}.
    
Rules:
1. Output ONLY a valid JSON object matching the exact structure below.
2. Translate ONLY reader-facing text fields (title, summary_1line, why_it_matters, and titles in also_covered).
3. Do NOT translate URLs.
4. Keep the same array order for also_covered.
5. Preserve technical terms, product names, and company names.

Source JSON:
{json.dumps(source_json, ensure_ascii=False, indent=2)}
"""
    raw = _chat_completion(
        base_url, model,
        [
            {"role": "system", "content": "You are a precise technical translator. Output valid JSON only."},
            {"role": "user", "content": prompt}
        ]
    )
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text, count=1)
        text = re.sub(r"\n?```\s*$", "", text, count=1)
    
    text = _repair_unescaped_quotes(text)
    translated = json.loads(text)
    
    res = {
        "translation_key": _translation_key(it),
        "id": it.get("id"),
        "source_hash": _source_hash(it),
        "title": translated.get("title") or it.get("title"),
        "summary_1line": translated.get("summary_1line") or it.get("summary_1line"),
        "why_it_matters": translated.get("why_it_matters") or it.get("why_it_matters"),
    }
    
    # Merge also_covered
    if it.get("also_covered"):
        trans_ac = translated.get("also_covered", [])
        merged_ac = []
        for idx, entry in enumerate(it["also_covered"]):
            t_title = entry.get("title")
            if idx < len(trans_ac) and isinstance(trans_ac[idx], dict):
                t_title = trans_ac[idx].get("title", t_title)
            merged_ac.append({
                "url": entry.get("url"),
                "title": t_title
            })
        res["also_covered"] = merged_ac
        
    return res

def main():
    parser = argparse.ArgumentParser(description="Build the localized live feed snapshot.")
    parser.add_argument("--locale", default="ko")
    parser.add_argument("--label", default="brief")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--base-url", default="http://localhost:1234/v1")
    parser.add_argument("--model", default="google/gemma-4-e4b")
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

    # Check LM studio connectivity if we actually need to translate anything
    to_translate = []
    max_translations = 20
    
    for it in dirty_targets:
        if len(to_translate) < max_translations:
            to_translate.append((it, True))  # (item, is_target)
            
    for it in dirty_lookahead:
        if len(to_translate) < max_translations:
            to_translate.append((it, False))  # (item, is_target)
            
    if to_translate:
        try:
            import urllib.request
            health_url = f"{args.base_url.rstrip('/')}/models"
            req = urllib.request.Request(health_url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                pass
        except Exception as exc:
            print(f"ERROR: Cannot reach LM Studio at {args.base_url}: {exc}", file=sys.stderr)
            sys.exit(1)

    # Translate
    results_map = {k: v for k, v in existing.items()}
    newly_translated = {}
    successes = 0
    failures = 0
    target_failures = 0
    
    if to_translate:
        print(f"Translating up to {len(to_translate)} items (budget: {max_translations})...")
        for idx, (it, is_target) in enumerate(to_translate, 1):
            t_key = _translation_key(it)
            role_str = "target" if is_target else "lookahead"
            print(f"  [{idx}/{len(to_translate)}] TRANSLATING ({role_str}): {it.get('title')[:60]}...", end="", flush=True)
            try:
                trans = _translate_item(it, args.locale, args.base_url, args.model)
                newly_translated[t_key] = trans
                results_map[t_key] = trans
                successes += 1
                print(" done")
            except Exception as e:
                print(f" FAILED: {e}")
                failures += 1
                if is_target:
                    target_failures += 1
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
        "model": args.model,
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
