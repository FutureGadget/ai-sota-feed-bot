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


if __name__ == "__main__":
    main()
