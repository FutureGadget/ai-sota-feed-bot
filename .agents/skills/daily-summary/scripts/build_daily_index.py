"""Validate daily recaps and rebuild the index the web/API serve from.

Scans ``data/daily/<date>.json`` files, validates each against the recap
schema, then writes:

- ``data/daily/index.json``  -> list of recap summaries (newest first)
- ``data/daily/latest.json`` -> the most recent recap in full

Run this after an agent writes a new recap (the SKILL does this automatically).

Usage:
    python build_daily_index.py            # rebuild + validate
    python build_daily_index.py --check    # validate only, non-zero exit on error
"""

from __future__ import annotations

import argparse
import subprocess
import sys

from daily_common import DATE_FILE_RE, DAILY_DIR, ROOT, load_json, validate_recap, write_json


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="validate only; do not write index")
    args = ap.parse_args()

    recap_files = sorted(
        p for p in DAILY_DIR.glob("*.json") if DATE_FILE_RE.match(p.name)
    )

    entries = []
    errors_total = 0
    for path in recap_files:
        data = load_json(path, None)
        errs = validate_recap(data)
        if errs:
            errors_total += len(errs)
            print(f"[invalid] {path.name}:", file=sys.stderr)
            for e in errs:
                print(f"  - {e}", file=sys.stderr)
            continue
        article_count = sum(len(c.get("articles", [])) for c in data.get("categories", []))
        entries.append(
            {
                "date": data["date"],
                "title": data["title"],
                "generated_at": data.get("generated_at"),
                "article_count": data.get("article_count", article_count),
                "category_count": len(data.get("categories", [])),
                "path": path.name,
            }
        )

    entries.sort(key=lambda e: str(e.get("date")), reverse=True)

    if args.check:
        if errors_total:
            print(f"validation failed: {errors_total} error(s)", file=sys.stderr)
            sys.exit(1)
        print(f"ok: {len(entries)} recap(s) valid")
        return

    write_json(DAILY_DIR / "index.json", entries)
    if entries:
        latest = load_json(DAILY_DIR / entries[0]["path"], None)
        if latest is not None:
            write_json(DAILY_DIR / "latest.json", latest)

    print(f"index rebuilt: {len(entries)} recap(s)" + (f", {errors_total} skipped (invalid)" if errors_total else ""))

    # Refresh the pre-rendered /daily/<date> pages + sitemap (SEO/link previews).
    render = ROOT / "pipeline" / "render_static_pages.py"
    subprocess.run([sys.executable, str(render)], check=True)

    if errors_total:
        sys.exit(1)


if __name__ == "__main__":
    main()
