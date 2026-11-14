#!/usr/bin/env python3
"""Check that a video storyboard covers the recap it explains.

Usage: check_coverage.py --kind daily|weekly --id KEY --narration narration.json --coverage coverage.json

coverage.json:
  {"highlights": [{"i": 0, "scene": "s2"}, {"i": 3, "cut": "reason"}, ...],
   "categories": [{"slug": "<category slug>", "scene": "s4"}, {"slug": "...", "cut": "reason"}],
   "lead": 0}

`i` indexes recap `highlights`. `lead` is the highlight index the lead story
comes from. Exit 0 when the mapping is complete, else print the problems and
exit 1.
"""
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
MAX_CUT_HIGHLIGHTS = 2
MAX_CUT_CATEGORIES = 1


def check(recap: dict, narration: list, coverage: dict) -> list[str]:
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
    lead = coverage.get("lead")
    cut_ids = {r.get("i") for r in coverage.get("highlights") or [] if r.get("scene") is None}
    if not isinstance(lead, int) or not 0 <= lead < len(highlights):
        errors.append("lead: must be a highlight index")
    elif lead in cut_ids:
        errors.append("lead: the lead highlight cannot be cut")
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
    errors = check(recap, narration, coverage)
    if errors:
        print("\n".join(errors))
        sys.exit(1)
    print("coverage ok")


if __name__ == "__main__":
    main()
