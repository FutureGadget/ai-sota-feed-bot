#!/usr/bin/env python3
"""Deployment artifact checks for the Cloudflare Worker deployment.

The Vercel serverless-function model is retired. Pages are static assets staged
into ``public/``, the API runs inside one Worker module graph, and R2 holds only
the JSON keys the Worker preloads. Four things still have hard limits:

1. **Requirements hygiene** - the deploy build installs root ``requirements.txt``
   in a job that also renders 148 daily, 6,882 story, and 180 model pages.
   Heavy batch/offline stacks (pandas, torch, pyarrow) do not belong there.
2. **Worker bundle** - ``wrangler`` uploads ``worker/`` as one script; Workers
   cap a compressed module at 10 MB.
3. **Static assets** - Workers Assets allows 20,000 files and 25 MiB per file.
   ``web/`` is ~8k files today, so the file count is the limit that can creep.
4. **Handler layout** - shared JS lives in ``lib/`` so the Worker imports it as a
   module, never under ``api/`` (that rule mattered when ``api/**`` was deployed
   as functions; keeping it avoids a stray handler-shaped file).

Usage:
    python scripts/check_deploy_artifacts.py [--max-assets 20000] [--verbose]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "requirements.txt"
WORKER_DIR = ROOT / "worker"
WEB_DIR = ROOT / "web"
API_DIR = ROOT / "api"

MAX_ROOT_REQUIREMENTS_COUNT = 20
MAX_WORKER_MB = 5.0
WORKERS_MAX_ASSETS = 20_000
WORKERS_MAX_FILE_MB = 25.0

# Heavy batch/offline dependencies. Install them in the workflow that needs them
# (models refresh, video render) instead of the site build.
PROHIBITED_PACKAGES = {
    "pyarrow",
    "pandas",
    "numpy",
    "scipy",
    "torch",
    "torchvision",
    "torchaudio",
    "transformers",
    "scikit-learn",
    "sklearn",
    "matplotlib",
    "polars",
    "duckdb",
    "tensorflow",
    "jax",
    "jaxlib",
    "boto3",
    "playwright",
    "selenium",
    "spacy",
    "nltk",
    "opencv-python",
    "cv2",
}


def check_requirements(requirements_path: Path) -> list[str]:
    """Ensure requirements.txt does not contain prohibited heavy packages."""
    errors: list[str] = []
    if not requirements_path.is_file():
        return [f"requirements.txt not found at {requirements_path}"]

    package_count = 0
    for line_no, raw_line in enumerate(
        requirements_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        package_count += 1
        package = re.split(r"[=<>~;]", line)[0].strip().lower()
        if package in PROHIBITED_PACKAGES:
            errors.append(
                f"requirements.txt:{line_no}: heavy package '{package}' does not belong in the "
                "site build; install it in the workflow that needs it"
            )

    if package_count > MAX_ROOT_REQUIREMENTS_COUNT:
        errors.append(
            f"requirements.txt has {package_count} packages (budget {MAX_ROOT_REQUIREMENTS_COUNT})"
        )
    return errors


def _dir_size_mb(path: Path, skip: tuple[str, ...] = ("node_modules", ".wrangler")) -> float:
    total = 0
    for item in path.rglob("*"):
        if not item.is_file():
            continue
        if any(part in skip for part in item.parts):
            continue
        total += item.stat().st_size
    return total / (1024 * 1024)


def check_worker_bundle(worker_dir: Path, max_mb: float = MAX_WORKER_MB) -> tuple[list[str], float]:
    if not worker_dir.is_dir():
        return [f"worker/ not found at {worker_dir}"], 0.0
    size_mb = _dir_size_mb(worker_dir)
    if size_mb > max_mb:
        return [f"worker/ is {size_mb:.2f} MB (budget {max_mb:.1f} MB)"], size_mb
    return [], size_mb


def check_static_assets(
    web_dir: Path,
    max_files: int = WORKERS_MAX_ASSETS,
    max_file_mb: float = WORKERS_MAX_FILE_MB,
) -> tuple[list[str], dict[str, float | int]]:
    """Workers Assets caps the file count, not (meaningfully) the total size."""
    if not web_dir.is_dir():
        return [f"web/ not found at {web_dir}"], {"files": 0, "mb": 0.0}
    errors: list[str] = []
    files = 0
    total = 0
    oversized: list[tuple[str, float]] = []
    for item in web_dir.rglob("*"):
        if not item.is_file():
            continue
        files += 1
        size_mb = item.stat().st_size / (1024 * 1024)
        total += size_mb
        if size_mb > max_file_mb:
            oversized.append((str(item.relative_to(web_dir)), size_mb))
    if files > max_files:
        errors.append(f"web/ has {files} files (Workers Assets cap {max_files})")
    for name, size_mb in oversized[:5]:
        errors.append(f"web/{name} is {size_mb:.1f} MB (per-file cap {max_file_mb:.0f} MiB)")
    return errors, {"files": files, "mb": total}


def check_handler_layout(api_dir: Path) -> list[str]:
    """Handlers are plain ES modules imported by the Worker; shared code is lib/."""
    if not api_dir.is_dir():
        return []
    nested = sorted(
        str(path.relative_to(api_dir)) for path in api_dir.rglob("*") if path.is_dir()
    )
    return [f"api/{name} is a directory; shared JS belongs in lib/" for name in nested]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-assets", type=int, default=WORKERS_MAX_ASSETS)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    errors: list[str] = []
    errors += check_requirements(REQUIREMENTS)
    worker_errors, worker_mb = check_worker_bundle(WORKER_DIR)
    errors += worker_errors
    asset_errors, assets = check_static_assets(WEB_DIR, max_files=args.max_assets)
    errors += asset_errors
    errors += check_handler_layout(API_DIR)

    if args.verbose:
        for title, items in (
            ("requirements", [p for p in (REQUIREMENTS,) if p.is_file()]),
            ("worker", [p for p in (WORKER_DIR,) if p.is_dir()]),
            ("assets", [p for p in (WEB_DIR,) if p.is_dir()]),
        ):
            print(f"checked {title}: {len(items)} path(s)")

    if errors:
        print("\nDeployment artifact check FAILED:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("Deployment artifact check PASSED.")
    print(
        f"   worker bundle: {worker_mb:.2f} MB / {MAX_WORKER_MB:.1f} MB"
        f" | static assets: {assets['files']} files ({assets['mb']:.0f} MB)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
