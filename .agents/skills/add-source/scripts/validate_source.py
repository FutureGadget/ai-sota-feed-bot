#!/usr/bin/env python3
"""Validate that a source actually reaches the feed end-to-end.

Adding a source to config/sources.yaml only makes the collector *fetch* it.
Whether its items reach data/processed/latest.json depends on a gauntlet of
ranking gates (slot mapping -> per-slot freshness window -> global pool cap ->
slot caps -> global merge -> top band). This script walks the same gauntlet for
one source and reports exactly where its items survive or die, so a newly added
source is never silently invisible.

Usage:
    python .agents/skills/add-source/scripts/validate_source.py --source NAME
    python .agents/skills/add-source/scripts/validate_source.py \
        --source google_cloud_blog --url-contains open-knowledge-format
    python .agents/skills/add-source/scripts/validate_source.py \
        --source NAME --items data/tier1/latest.json

Exit code is 0 when at least one item from the source reaches the final feed
(or, with --url-contains, the specified item does), 1 otherwise — so it can
gate CI or a pre-merge check.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "pipeline"))

import ranking  # noqa: E402
from ranking import (  # noqa: E402
    _age_hours,
    _build_source_slot_map,
    _freshness_score,
    load_ranking_config,
    run_ranking,
)


def _load_items(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("items", data) if isinstance(data, dict) else data


def _load_profile() -> dict:
    import yaml

    p = ROOT / "config" / "profile.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}


def _load_source_health() -> dict[str, float]:
    p = ROOT / "data" / "health" / "source_health.json"
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {s: float(r.get("reliability", 1.0)) for s, r in payload.get("sources", {}).items()}


def _load_llm_cfg() -> dict:
    import yaml

    p = ROOT / "config" / "llm.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {"enabled": False}


def _classify_prefilter(item, cfg, profile, source_health, slot):
    """Replicate ranking.stage_a_prefilter's per-item gates so we can attribute
    a drop reason (the function itself only returns survivors)."""
    exclude = profile.get("selection", {}).get("exclude_title_regex", []) or []
    if any(re.search(pat, item.get("title", "")) for pat in exclude):
        return "hard_exclude", None
    scfg = (cfg.get("slots", {}) or {}).get(slot, {})
    fresh_h = float(scfg.get("freshness_hours", 72))
    age = _age_hours(item.get("published", ""))
    if age > fresh_h:
        return "freshness_window", None
    rel = float(source_health.get(item.get("source", ""), 1.0))
    if rel < 0.3:
        return "health_floor", None
    fr = _freshness_score(item.get("published", ""), decay_hours=max(12.0, fresh_h / 3))
    return "pass", round(fr + rel, 3)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True, help="source name as in config/sources.yaml")
    ap.add_argument("--url-contains", default=None, help="optional substring of a specific item URL to track")
    ap.add_argument("--items", default="data/tier1/latest.json", help="candidate items file (default: tier1 latest)")
    args = ap.parse_args()

    items_path = (ROOT / args.items) if not Path(args.items).is_absolute() else Path(args.items)
    if not items_path.exists():
        print(f"ERROR: items file not found: {items_path}")
        return 1

    items = _load_items(items_path)
    cfg = load_ranking_config()
    profile = _load_profile()
    source_health = _load_source_health()
    src_to_slot = _build_source_slot_map(cfg)

    src = args.source
    slot = src_to_slot.get(src, "overflow")
    pool_cap = int(cfg.get("candidate_pool_cap", 120))
    mine = [it for it in items if it.get("source") == src]

    print(f"\n=== validate_source: {src} ===")
    print(f"items file       : {items_path.relative_to(ROOT) if items_path.is_relative_to(ROOT) else items_path}")
    print(f"slot mapping     : {slot}" + ("   ⚠️  UNMAPPED -> overflow (add it to a slot in config/ranking.yaml!)" if src not in src_to_slot else ""))
    print(f"collected items  : {len(mine)}")
    if not mine:
        print("  ⚠️  0 items collected. Check config/sources.yaml (name/url/type) and that the collector has run.")
        return 1

    # --- Stage A: prefilter (per-item drop reasons) ---
    survivors, diag = ranking.stage_a_prefilter(items, cfg, profile, source_health)
    survivor_keys = {(s.get("url") or "", s.get("title") or "") for s in survivors}

    # Global pool-cap cutoff: the lowest prefilter_score that made the pool.
    cutoff = min((s.get("prefilter_score", 0.0) for s in survivors), default=0.0)

    passed, dropped = [], []
    for it in mine:
        reason, score = _classify_prefilter(it, cfg, profile, source_health, slot)
        in_pool = (it.get("url") or "", it.get("title") or "") in survivor_keys
        if reason == "pass" and in_pool:
            passed.append((it, score))
        elif reason == "pass" and not in_pool:
            dropped.append((it, f"pool_cap (score {score} < cutoff {cutoff})"))
        else:
            dropped.append((it, reason))

    print(f"\nStage A prefilter (pool_cap={pool_cap}, cutoff_score={round(cutoff,3)}):")
    print(f"  passed into candidate pool : {len(passed)}")
    print(f"  dropped                    : {len(dropped)}")
    for it, why in dropped[:10]:
        print(f"    - DROP [{why}]  {it.get('title','')[:60]}")

    # --- Full ranking: final feed presence ---
    top, _ = run_ranking(items, profile, _load_llm_cfg(), source_health)
    in_feed = [it for it in top if it.get("source") == src]
    print(f"\nFinal feed (data/processed/latest.json shape): {len(top)} items")
    print(f"  items from {src} in final feed: {len(in_feed)}")
    for it in in_feed:
        print(f"    ✓ slot={it.get('slot')} final={it.get('final_score')} global={it.get('global_score')}  {it.get('title','')[:55]}")

    # --- Optional: track a specific item ---
    target_ok = True
    if args.url_contains:
        sub = args.url_contains
        coll = [it for it in mine if sub in (it.get("url") or "")]
        fed = [it for it in in_feed if sub in (it.get("url") or "")]
        print(f"\nTracked item (url contains '{sub}'):")
        print(f"  collected : {bool(coll)}")
        if coll:
            r, s = _classify_prefilter(coll[0], cfg, profile, source_health, slot)
            inp = (coll[0].get("url") or "", coll[0].get("title") or "") in survivor_keys
            print(f"  prefilter : {'pass' if (r=='pass' and inp) else (r if r!='pass' else 'pool_cap')}  (score {s})")
        print(f"  in feed   : {bool(fed)}")
        target_ok = bool(fed)

    # --- Verdict + hints ---
    exposed = bool(in_feed) and target_ok
    print("\n=== VERDICT ===")
    if exposed:
        print(f"✅ EXPOSED — {src} reaches the feed.")
        return 0

    print(f"❌ NOT EXPOSED — {src} is not reaching the feed. Likely fix:")
    if src not in src_to_slot:
        print("  • Source is UNMAPPED. Add it to an appropriate slot's `sources:` in")
        print("    config/ranking.yaml AND config/presets/<active-preset>.yaml.")
    elif any("pool_cap" in str(w) for _, w in dropped) and not passed:
        print("  • Dropped at candidate_pool_cap (slot-scaled freshness decay crowds out")
        print("    short-window sources). Raise candidate_pool_cap, or move the source to")
        print("    a slot with a longer freshness_hours window.")
    elif any(w == "freshness_window" for _, w in dropped) and not passed:
        print(f"  • All items older than the slot freshness window. Raise `{slot}.freshness_hours`")
        print("    or expect this low-volume source to surface only right after it publishes.")
    elif any(w == "health_floor" for _, w in dropped):
        print("  • Source reliability < 0.3 (circuit breaker). Check data/health/source_health.json.")
    elif passed and not in_feed:
        print(f"  • Items enter the pool but lose the `{slot}` slot to higher-scored items.")
        print(f"    Raise `{slot}.max_items`/`max_per_source`, lift `source_bias.{src}`, or give")
        print("    the source its own slot (+ a dynamic_slot_rerank.base_bias entry).")
    else:
        print("  • Mixed signal — inspect the per-item drops above.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
