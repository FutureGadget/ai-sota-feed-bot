"""Validate the agent-confirmed scout links against the schema.

Checks data/storylines/scout/links.json structurally and, when the candidate
bundle is present, that every member sid belongs to the current storyline
window. The allowlist includes accepted links after they stop appearing as
candidates and members of an existing storyline being extended. A link whose
members age out is harmless — the floor gate makes it inert — but is reported
so the routine can prune it.

Usage:
    python validate_links.py            # validate (non-zero exit on error)
    python validate_links.py --check    # explicit alias for CI
"""

from __future__ import annotations

import argparse
import sys

from scout_common import (
    CANDIDATES_FILE,
    LINKS_FILE,
    candidate_sids,
    load_json,
    load_links,
    validate_links,
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    ap.parse_args()

    if not LINKS_FILE.exists():
        print("no scout links yet (data/storylines/scout/links.json absent)")
        return

    links = load_links()
    # Only cross-check sids when the candidate bundle exists; otherwise validate
    # structure alone (the bundle may have been pruned between runs).
    valid = candidate_sids() if CANDIDATES_FILE.exists() else None
    errors = validate_links(links, valid_sids=valid)

    for e in errors:
        print(f"[invalid] {e}", file=sys.stderr)

    print(f"scout links: {len(links)} total, {len(errors)} errors")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
