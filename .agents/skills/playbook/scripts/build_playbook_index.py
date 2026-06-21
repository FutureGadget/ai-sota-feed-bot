"""Validate Playbook editions and rebuild the index the web/API serve from.

Scans ``data/playbook/<date>.json`` files, validates each against the edition
schema, then writes:

- ``data/playbook/index.json``  -> list of edition summaries (newest first)
- ``data/playbook/latest.json`` -> the most recent edition in full

Run this after an agent writes a new edition (the SKILL does this
automatically). The /playbook page + /api/playbook read these two files.

Usage:
    python build_playbook_index.py            # rebuild + validate
    python build_playbook_index.py --check    # validate only, non-zero on error
"""

from __future__ import annotations

import argparse
import sys

from playbook_common import (
    DATE_FILE_RE,
    PLAYBOOK_DIR,
    load_json,
    validate_edition,
    write_json,
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="validate only; do not write index")
    args = ap.parse_args()

    edition_files = sorted(
        p for p in PLAYBOOK_DIR.glob("*.json") if DATE_FILE_RE.match(p.name)
    )

    entries = []
    errors_total = 0
    for path in edition_files:
        data = load_json(path, None)
        errs = validate_edition(data)
        if errs:
            errors_total += len(errs)
            print(f"[invalid] {path.name}:", file=sys.stderr)
            for e in errs:
                print(f"  - {e}", file=sys.stderr)
            continue
        cards = data.get("cards", [])
        entries.append(
            {
                "date": data["date"],
                "title": data["title"],
                "generated_at": data.get("generated_at"),
                "card_count": data.get("card_count", len(cards)),
                "path": path.name,
            }
        )

    entries.sort(key=lambda e: str(e.get("date")), reverse=True)

    if args.check:
        if errors_total:
            print(f"validation failed: {errors_total} error(s)", file=sys.stderr)
            sys.exit(1)
        print(f"ok: {len(entries)} edition(s) valid")
        return

    write_json(PLAYBOOK_DIR / "index.json", entries)
    if entries:
        latest = load_json(PLAYBOOK_DIR / entries[0]["path"], None)
        if latest is not None:
            write_json(PLAYBOOK_DIR / "latest.json", latest)

    print(
        f"index rebuilt: {len(entries)} edition(s)"
        + (f", {errors_total} skipped (invalid)" if errors_total else "")
    )

    if errors_total:
        sys.exit(1)


if __name__ == "__main__":
    main()
