#!/usr/bin/env python3
"""Check deployment bundle size, requirements budget, and .vercelignore integrity.

Vercel's Serverless Functions enforce a strict unzipped maximum size of 250 MB.
Because Vercel bundles the project into each serverless function (minus excludeFiles),
and installs root requirements.txt in the build environment, adding heavy dependencies
(e.g., pyarrow, pandas, torch) or omitting heavy runtime data from .vercelignore will
exceed the 250 MB limit and freeze deployments across production and preview.

This script enforces:
1. Requirements Hygiene: Prohibits heavy batch/offline dependencies (e.g. pyarrow,
   pandas, scipy, torch, numpy) in root requirements.txt.
2. .vercelignore Completeness: Ensures all known heavy runtime directories (data/raw,
   data/tier1/runs, etc.) are explicitly excluded from Vercel deployments.
3. Function Bundle Budgets: Calculates the unzipped bundle size for every function
   declared in vercel.json, ensuring none exceed a safe threshold (default: 150 MB).
4. Bundled Data Growth: Audits data directories bundled into functions to prevent
   retention creep from silently eroding headroom.

Usage:
    python scripts/check_bundle_size.py [--max-mb 150] [--verbose]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Packages that are known to be large (>20 MB unzipped) or intended only for
# batch/offline pipelines. These must NEVER be added to root requirements.txt
# because Vercel installs root requirements into the deployment container.
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

# Directories that carry heavy runtime or build data and must be excluded in .vercelignore.
MANDATORY_VERCELIGNORE_ENTRIES = (
    "data/raw",
    "data/tier1/runs",
    "data/llm",
    "data/health",
    "data/digest",
    "data/diagnostics",
    "data/cache",
    "data/analysis",
    "data/foundations/input",
    "data/playbook/lab/drafts",
    "data/models/history",
    "docs/assets",
    ".venv",
)

# Maximum allowed bundle size per serverless function (in MB).
# Vercel hard limit is 250 MB. 150 MB leaves a safe 100 MB buffer.
DEFAULT_MAX_FUNCTION_MB = 150.0

# Maximum allowed number of top-level dependencies in root requirements.txt
MAX_ROOT_REQUIREMENTS_COUNT = 10


def expand_braces(text: str) -> list[str]:
    """Expand bash-style brace patterns like {a,b} in a glob pattern string."""
    match = re.search(r"\{([^{}]+)\}", text)
    if not match:
        return [text]
    prefix = text[: match.start()]
    suffix = text[match.end() :]
    parts = match.group(1).split(",")
    res: list[str] = []
    for p in parts:
        res.extend(expand_braces(prefix + p.strip() + suffix))
    return res


def check_requirements(requirements_path: Path) -> list[str]:
    """Ensure requirements.txt does not contain prohibited heavy packages."""
    errors: list[str] = []
    if not requirements_path.is_file():
        errors.append(f"requirements.txt not found at {requirements_path}")
        return errors

    lines = requirements_path.read_text(encoding="utf-8").splitlines()
    pkg_count = 0
    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        pkg_count += 1
        # Extract package name before ==, >=, <=, ~=, <, >, etc.
        pkg_name = re.split(r"[=<>~;]", line)[0].strip().lower()
        if pkg_name in PROHIBITED_PACKAGES:
            errors.append(
                f"requirements.txt:{line_no}: Prohibited heavy package '{pkg_name}' found! "
                f"Heavy packages inflate Vercel function bundles and risk exceeding the 250 MB limit. "
                f"Install '{pkg_name}' only in workflow-specific jobs (e.g. in .github/workflows/models-refresh.yml) "
                f"or in a separate requirements file."
            )

    if pkg_count > MAX_ROOT_REQUIREMENTS_COUNT:
        errors.append(
            f"requirements.txt contains {pkg_count} packages (max budget is {MAX_ROOT_REQUIREMENTS_COUNT}). "
            f"Keep root requirements.txt minimal for Vercel."
        )

    return errors


def check_vercelignore(vercelignore_path: Path) -> list[str]:
    """Ensure all mandatory heavy directories are excluded in .vercelignore."""
    errors: list[str] = []
    if not vercelignore_path.is_file():
        errors.append(f".vercelignore not found at {vercelignore_path}")
        return errors

    content = vercelignore_path.read_text(encoding="utf-8")
    lines = {
        line.strip().rstrip("/")
        for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    }

    for entry in MANDATORY_VERCELIGNORE_ENTRIES:
        normalized = entry.rstrip("/")
        if normalized not in lines and (normalized + "/**") not in lines:
            errors.append(
                f".vercelignore is missing mandatory ignore entry: '{entry}'. "
                f"Excluding this directory is required to prevent serverless function bundles "
                f"from exceeding Vercel's 250 MB limit."
            )

    return errors


def get_function_bundle_files(
    root: Path,
    fn_name: str,
    fn_cfg: dict,
) -> set[Path]:
    """Compute the set of files included in a function bundle."""
    matched_files: set[Path] = set()

    # Always include the function file itself and local imported libraries
    fn_file = root / fn_name
    if fn_file.is_file():
        matched_files.add(fn_file)

    # If the function is updates.js or uses editorial-catalog.js, include it
    lib_catalog = root / "lib" / "editorial-catalog.js"
    if lib_catalog.is_file():
        matched_files.add(lib_catalog)

    inc_str = fn_cfg.get("includeFiles") or ""
    inc_patterns: list[str] = []
    for token in inc_str.split():
        inc_patterns.extend(expand_braces(token))

    for pat in inc_patterns:
        full_pat = str(root / pat)
        for match in glob.glob(full_pat, recursive=True):
            p = Path(match)
            if p.is_file():
                matched_files.add(p)

    exc_str = fn_cfg.get("excludeFiles") or ""
    exc_patterns: list[str] = []
    for token in exc_str.split():
        exc_patterns.extend(expand_braces(token))

    excluded_files: set[Path] = set()
    for pat in exc_patterns:
        full_pat = str(root / pat)
        for match in glob.glob(full_pat, recursive=True):
            p = Path(match)
            if p.is_file():
                excluded_files.add(p)

    return matched_files - excluded_files


def check_function_bundles(
    root: Path,
    vercel_json_path: Path,
    max_mb: float = DEFAULT_MAX_FUNCTION_MB,
    verbose: bool = False,
) -> tuple[list[str], dict[str, float]]:
    """Compute unzipped bundle sizes for each function declared in vercel.json."""
    errors: list[str] = []
    sizes: dict[str, float] = {}

    if not vercel_json_path.is_file():
        errors.append(f"vercel.json not found at {vercel_json_path}")
        return errors, sizes

    try:
        cfg = json.loads(vercel_json_path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"Failed to parse vercel.json: {exc}")
        return errors, sizes

    functions = cfg.get("functions", {})
    if not functions:
        errors.append("No functions defined under 'functions' key in vercel.json")
        return errors, sizes

    max_bytes = max_mb * 1024 * 1024

    for fn_name, fn_cfg in functions.items():
        bundle_files = get_function_bundle_files(root, fn_name, fn_cfg)
        total_bytes = sum(f.stat().st_size for f in bundle_files if f.is_file())
        size_mb = total_bytes / (1024 * 1024)
        sizes[fn_name] = size_mb

        if verbose:
            print(f"  {fn_name:24}: {len(bundle_files):5} files, {size_mb:6.2f} MB")

        if total_bytes > max_bytes:
            top_files = sorted(
                [(f.stat().st_size, f.relative_to(root)) for f in bundle_files if f.is_file()],
                key=lambda x: -x[0],
            )[:5]
            top_breakdown = ", ".join(f"{rel} ({sz / (1024*1024):.1f} MB)" for sz, rel in top_files)
            errors.append(
                f"Function '{fn_name}' bundle size ({size_mb:.2f} MB) exceeds maximum allowed {max_mb:.1f} MB! "
                f"Largest files: {top_breakdown}. "
                f"Vercel enforces a 250 MB hard limit; adjust includeFiles/excludeFiles or prune data retention."
            )

    return errors, sizes


def check_bundled_data_growth(root: Path) -> list[str]:
    """Audit the physical sizes of bundled data subdirectories to prevent retention creep."""
    errors: list[str] = []
    dir_budgets_mb = {
        "data/processed": 100.0,
        "data/stories": 30.0,
        "data/storylines": 20.0,
        "data/daily": 20.0,
        "data/weekly": 20.0,
        "data/wiki": 10.0,
        "data/playbook": 15.0,
        "data/foundations": 15.0,
    }

    for rel_dir, max_mb in dir_budgets_mb.items():
        p = root / rel_dir
        if not p.is_dir():
            continue
        total_bytes = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        size_mb = total_bytes / (1024 * 1024)
        if size_mb > max_mb:
            errors.append(
                f"Directory '{rel_dir}' size ({size_mb:.2f} MB) exceeds budget of {max_mb:.1f} MB. "
                f"Review data retention policies before merging."
            )

    return errors


def run_checks(
    root: Path = ROOT,
    max_mb: float = DEFAULT_MAX_FUNCTION_MB,
    verbose: bool = False,
) -> bool:
    """Run all bundle size and dependency hygiene checks."""
    all_errors: list[str] = []

    if verbose:
        print(f"=== Checking requirements.txt hygiene ===")
    req_errors = check_requirements(root / "requirements.txt")
    all_errors.extend(req_errors)

    if verbose:
        print(f"=== Checking .vercelignore completeness ===")
    vignore_errors = check_vercelignore(root / ".vercelignore")
    all_errors.extend(vignore_errors)

    if verbose:
        print(f"=== Checking vercel.json function bundle sizes (budget: {max_mb:.1f} MB) ===")
    fn_errors, fn_sizes = check_function_bundles(
        root, root / "vercel.json", max_mb=max_mb, verbose=verbose
    )
    all_errors.extend(fn_errors)

    if verbose:
        print(f"=== Auditing bundled data directories ===")
    data_errors = check_bundled_data_growth(root)
    all_errors.extend(data_errors)

    if all_errors:
        print("\n❌ Deployment Bundle Size & Hygiene Check FAILED with errors:", file=sys.stderr)
        for err in all_errors:
            print(f"  • {err}", file=sys.stderr)
        return False

    print("✅ Deployment bundle size and dependency hygiene check PASSED.")
    if not verbose:
        # Print a concise summary
        max_fn = max(fn_sizes.items(), key=lambda x: x[1]) if fn_sizes else ("none", 0.0)
        print(f"   Functions checked: {len(fn_sizes)} | Largest: {max_fn[0]} ({max_fn[1]:.2f} MB / {max_mb:.1f} MB budget)")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify Vercel serverless function bundle sizes and requirements budget."
    )
    parser.add_argument(
        "--max-mb",
        type=float,
        default=DEFAULT_MAX_FUNCTION_MB,
        help=f"Maximum allowed unzipped size per function in MB (default: {DEFAULT_MAX_FUNCTION_MB})",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print verbose bundle size details per function",
    )
    args = parser.parse_args()

    success = run_checks(root=ROOT, max_mb=args.max_mb, verbose=args.verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
