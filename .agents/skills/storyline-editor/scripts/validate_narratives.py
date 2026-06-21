"""Validate storyline narrative sidecars against the schema.

Scans ``data/storylines/narratives/*.json``, validates each against
``NARRATIVE_SCHEMA``, and reports staleness against the current storyline index
(a stale narrative is still valid — it just predates the thread's latest
update and should be refreshed).

Usage:
    python validate_narratives.py            # report (non-zero exit on schema error)
    python validate_narratives.py --check    # same; explicit alias for CI
"""

from __future__ import annotations

import argparse
import sys

from storyline_common import (
    NARRATIVE_DIR,
    STORYLINES_INDEX,
    load_json,
    member_sids,
    narrative_is_fresh,
    validate_narrative,
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="validate only (default behavior)")
    ap.parse_args()

    index = load_json(STORYLINES_INDEX, {}) or {}
    entries = {s.get("slug"): s for s in index.get("storylines") or [] if s.get("slug")}

    files = sorted(NARRATIVE_DIR.glob("*.json")) if NARRATIVE_DIR.is_dir() else []
    if not files:
        print("no narrative sidecars yet (data/storylines/narratives/ is empty)")
        return

    errors_total = 0
    stale = []
    ok = 0
    for path in files:
        data = load_json(path, None)
        entry = entries.get(path.stem)
        valid_sids = set(member_sids(entry)) if entry else None
        detail = load_json(NARRATIVE_DIR.parent / f"{path.stem}.json", {}) or {}
        displayed_sids = set(member_sids(detail)) if detail else None
        errs = validate_narrative(
            data,
            valid_sids=valid_sids,
            required_beat_sids=displayed_sids,
        )
        if errs:
            errors_total += len(errs)
            print(f"[invalid] {path.name}:", file=sys.stderr)
            for e in errs:
                print(f"  - {e}", file=sys.stderr)
            continue
        ok += 1
        if entry and not narrative_is_fresh(data, entry):
            stale.append(path.stem)

    print(f"narratives: {ok} valid, {errors_total} errors across {len(files)} files")
    if stale:
        print(f"stale (thread moved on, refresh recommended): {', '.join(stale)}")

    if errors_total:
        sys.exit(1)


if __name__ == "__main__":
    main()
