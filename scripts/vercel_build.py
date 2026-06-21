#!/usr/bin/env python3
"""Render static pages and stage the Vercel static output tree."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = ROOT / "public"
PUBLIC_WEB_DIR = PUBLIC_DIR / "web"


def main() -> None:
    # Recompile the agent-engineering wiki from its committed markdown pages so
    # code-only PR previews reflect edited pages. Non-fatal: a broken page falls
    # back to the committed data/wiki/index.json rather than failing the deploy.
    wiki = subprocess.run([sys.executable, "pipeline/build_wiki.py"], cwd=ROOT)
    if wiki.returncode != 0:
        print("warning: build_wiki.py failed; using committed index.json", file=sys.stderr)
    subprocess.run(
        [sys.executable, "pipeline/render_static_pages.py"],
        cwd=ROOT,
        check=True,
    )
    if PUBLIC_WEB_DIR.exists():
        shutil.rmtree(PUBLIC_WEB_DIR)
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "web", PUBLIC_WEB_DIR)
    print(f"vercel static output staged: {PUBLIC_WEB_DIR}")

    # Pages are served from /web/* via vercel.json rewrites, but the brand and
    # icon assets are referenced from the site root (e.g. /logo.png in emails
    # and the Organization JSON-LD, /favicon.svg, /og-default.png, the PWA
    # manifest). Vercel only serves files that physically exist under the output
    # dir, and rewrites are a fallback that never fires when a request has a
    # file extension, so these must be copied to the public root or they 404.
    root_assets = [p for p in (ROOT / "web").glob("*") if p.is_file() and p.suffix != ".html"]
    for asset in root_assets:
        shutil.copy2(asset, PUBLIC_DIR / asset.name)
    print(f"vercel root assets staged: {len(root_assets)} files")

    # The mascot is loaded via a root-relative ES module import (`/mascot/mascot.js`,
    # see web/mascot/README.md and the loader snippet in every page shell). Like the
    # brand assets above, a request with a file extension is served only if the file
    # physically exists at that path — the /web/* rewrites never fire for it. The
    # root-asset copy above is non-recursive, so the mascot subdirectory must be
    # staged to the public root explicitly or the import 404s and the mascot no-ops.
    mascot_src = ROOT / "web" / "mascot"
    if mascot_src.is_dir():
        shutil.copytree(mascot_src, PUBLIC_DIR / "mascot", dirs_exist_ok=True)
        print(f"vercel root assets staged: mascot/ -> {PUBLIC_DIR / 'mascot'}")


if __name__ == "__main__":
    main()
