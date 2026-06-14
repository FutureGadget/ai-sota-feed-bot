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
