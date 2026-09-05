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

# web/ subdirectories that must also exist at the deployment root because pages
# reference them with root-relative, extensioned URLs (see the staging step).
ROOT_ASSET_DIRS = ("mascot", "universe", "og", "lab-artifacts")


def main() -> None:
    # Lab records are authored source data. Refuse to publish if their validated
    # index or latest snapshot is missing or stale relative to those sources.
    subprocess.run(
        [sys.executable, "pipeline/build_skill_lab.py", "--check"],
        cwd=ROOT,
        check=True,
    )
    # Recompile the agent-engineering wiki from its committed markdown pages so
    # code-only PR previews reflect edited pages. Non-fatal: a broken page falls
    # back to the committed data/wiki/index.json rather than failing the deploy.
    wiki = subprocess.run([sys.executable, "pipeline/build_wiki.py"], cwd=ROOT)
    if wiki.returncode != 0:
        print("warning: build_wiki.py failed; using committed index.json", file=sys.stderr)
    foundations = subprocess.run([sys.executable, "pipeline/build_foundations.py"], cwd=ROOT)
    if foundations.returncode != 0:
        print("warning: build_foundations.py failed; using committed index.json", file=sys.stderr)
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

    # Asset subdirectories referenced root-relative from page markup:
    #   mascot/  -> `/mascot/mascot.js`   ES module import (every page shell)
    #   universe/-> `/universe/universe.js` ES module import (/map orbit view)
    #   og/      -> `/og/<name>.png`      per-edition og:image (pipeline/og_cards.py)
    #   lab-artifacts/ -> `/lab-artifacts/*` pinned Skill Lab evidence
    # Same rule as the brand assets above: a request with a file extension is
    # served only if the file physically exists at that path — the /web/*
    # rewrites never fire for it. The root-asset copy above is non-recursive,
    # so each of these must be staged to the public root explicitly or the
    # request 404s. Add any new root-relative asset dir here.
    for name in ROOT_ASSET_DIRS:
        src = ROOT / "web" / name
        if src.is_dir():
            shutil.copytree(src, PUBLIC_DIR / name, dirs_exist_ok=True)
            print(f"vercel root assets staged: {name}/ -> {PUBLIC_DIR / name}")


if __name__ == "__main__":
    main()
