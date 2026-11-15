#!/usr/bin/env python3
"""Check that a video storyboard covers the recap it explains.

Usage: check_coverage.py --kind daily|weekly --id KEY --narration narration.json --coverage coverage.json

coverage.json:
  {"highlights": [{"i": 0, "scene": "s2", "tier": "lead"}, {"i": 1, "scene": "s3", "tier": "deep"},
                  {"i": 2, "scene": "s5", "tier": "quick", "swap": "reason"}, {"i": 4, "cut": "reason"}],
   "categories": [{"slug": "<category slug>", "scene": "s4"}, {"slug": "...", "cut": "reason"}]}

`i` indexes recap `highlights`, which are in priority order. The lead and deep
tiers must be the first highlights in that order; a highlight that is skipped
for a lower-ranked one must be `quick` with a `swap` reason. Exit 0 when the
mapping is complete, else print the problems and exit 1.
"""
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
MAX_CUT_HIGHLIGHTS = 1
DEEP = {"daily": 2, "weekly": 3}
TIERS = ("lead", "deep", "quick")
MAX_CUT_CATEGORIES = 1


def check(recap: dict, narration: list, coverage: dict, kind: str = "daily") -> list[str]:
    errors: list[str] = []
    scenes = {s.get("id") for s in narration}
    highlights = recap.get("highlights") or []
    slugs = [c.get("slug") for c in recap.get("categories") or []]

    def entries(name: str, key: str, expected: list) -> int:
        rows = coverage.get(name) or []
        seen = [r.get(key) for r in rows]
        for want in expected:
            if want not in seen:
                errors.append(f"{name}: {key} {want!r} is not mapped")
        for r in rows:
            if r.get(key) not in expected:
                errors.append(f"{name}: unknown {key} {r.get(key)!r}")
            if r.get("scene") is not None and r["scene"] not in scenes:
                errors.append(f"{name}: scene {r['scene']!r} is not in narration.json")
            if r.get("scene") is None and not str(r.get("cut") or "").strip():
                errors.append(f"{name}: {key} {r.get(key)!r} needs a scene or a cut reason")
        return sum(1 for r in rows if r.get("scene") is None)

    cut_h = entries("highlights", "i", list(range(len(highlights))))
    cut_c = entries("categories", "slug", slugs)
    if cut_h > MAX_CUT_HIGHLIGHTS:
        errors.append(f"highlights: {cut_h} cut, at most {MAX_CUT_HIGHLIGHTS}")
    if cut_c > MAX_CUT_CATEGORIES:
        errors.append(f"categories: {cut_c} cut, at most {MAX_CUT_CATEGORIES}")
    rows = [r for r in coverage.get("highlights") or [] if r.get("scene") is not None and isinstance(r.get("i"), int)]
    for r in rows:
        if r.get("tier") not in TIERS:
            errors.append(f"highlights: i {r['i']} needs a tier of {', '.join(TIERS)}")
        if r.get("swap") is not None and (r.get("tier") != "quick" or not str(r["swap"]).strip()):
            errors.append(f"highlights: i {r['i']} swap needs tier quick and a reason")
    # Eligible = shown and not swapped out, in priority order. The first is the
    # lead and the next DEEP[kind] are deep, so depth follows the recap's ranking.
    eligible = sorted(r["i"] for r in rows if r.get("swap") is None)
    want_deep = eligible[1 : 1 + DEEP[kind]]
    tier = {r["i"]: r.get("tier") for r in rows}
    leads = sorted(i for i, t in tier.items() if t == "lead")
    deeps = sorted(i for i, t in tier.items() if t == "deep")
    if not eligible:
        errors.append("highlights: no lead; every shown highlight is swapped")
    elif leads != eligible[:1]:
        errors.append(f"highlights: lead must be highlight {eligible[0]}, got {leads}")
    if eligible and deeps != want_deep:
        errors.append(f"highlights: deep must be highlights {want_deep}, got {deeps}")
    by_scene: dict = {}
    for r in rows:
        if r.get("tier") in ("lead", "deep"):
            by_scene.setdefault(r["scene"], []).append(r["i"])
    for scene, ids in by_scene.items():
        if len(ids) > 1:
            errors.append(f"highlights: scene {scene!r} carries lead/deep highlights {ids}; one scene each")
    return errors


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=["daily", "weekly"], required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--narration", required=True)
    ap.add_argument("--coverage", required=True)
    a = ap.parse_args()
    recap = json.loads((ROOT / "data" / a.kind / f"{a.id}.json").read_text(encoding="utf-8"))
    narration = json.loads(Path(a.narration).read_text(encoding="utf-8"))
    coverage = json.loads(Path(a.coverage).read_text(encoding="utf-8"))
    errors = check(recap, narration, coverage, a.kind)
    if errors:
        print("\n".join(errors))
        sys.exit(1)
    print("coverage ok")


if __name__ == "__main__":
    main()
