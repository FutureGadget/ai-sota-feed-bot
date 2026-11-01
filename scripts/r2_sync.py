#!/usr/bin/env python3
"""Publish the API's data files to the Cloudflare R2 bucket.

The Vercel functions read committed data/ JSON from disk (vercel.json
includeFiles); the Cloudflare Worker reads the same files from R2 through the
injected data source. This script mirrors the exact set of files the API can
read into the bucket under data/<same relative path>.

Only changed files are uploaded: a sha256 manifest of the last publish is kept
in the bucket at _deploy/data-manifest.json, and files added/changed/removed
since then are synced. The first run uploads everything.

Required env:
  CLOUDFLARE_ACCOUNT_ID   - account that owns the bucket
  R2_ACCESS_KEY_ID        - R2 API token (S3 credentials, Object Read & Write)
  R2_SECRET_ACCESS_KEY
  R2_BUCKET               - bucket name (default: llm-digest-data)

Uses the AWS CLI (preinstalled on GitHub-hosted runners) against R2's
S3-compatible endpoint.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MANIFEST_KEY = "_deploy/data-manifest.json"

# Every file the API handlers can read at runtime. Directory entries are
# top-level only (no recursion): input/, drafts/, narratives/ and other
# pipeline-internal subtrees are never served.
EXACT_FILES = [
    "processed/latest.json",
    "processed/runs_index.json",
    "processed/editorial.json",
    "feedback/source_adjustments.json",
    "i18n/ko/feed/latest.json",
    "i18n/ko/feed/status.json",
    "stories/index.json",
    "wiki/index.json",
    "foundations/index.json",
]
TOP_LEVEL_DIRS = [
    "served",
    "daily",
    "weekly",
    "storylines",
    "playbook",
    "playbook/lab",
    "i18n/ko/playbook",
]


def collect_files() -> dict[str, Path]:
    files: dict[str, Path] = {}
    for rel in EXACT_FILES:
        p = DATA / rel
        if p.is_file():
            files[rel] = p
    for rel_dir in TOP_LEVEL_DIRS:
        d = DATA / rel_dir
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            if p.is_file() and p.suffix == ".json":
                files[f"{rel_dir}/{p.name}"] = p
    return files


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    bucket = os.environ.get("R2_BUCKET", "llm-digest-data")
    endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
    env = {
        **os.environ,
        "AWS_ACCESS_KEY_ID": os.environ["R2_ACCESS_KEY_ID"],
        "AWS_SECRET_ACCESS_KEY": os.environ["R2_SECRET_ACCESS_KEY"],
        "AWS_EC2_METADATA_DISABLED": "true",
    }

    def aws(*args: str, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["aws", "s3", "--endpoint-url", endpoint, "--region", "auto", *args],
            env=env, capture_output=True, text=True, check=check,
        )

    files = collect_files()
    manifest = {rel: sha256(p) for rel, p in files.items()}
    print(f"r2 sync: {len(manifest)} files in whitelist")

    previous: dict[str, str] = {}
    try:
        out = aws("cp", f"s3://{bucket}/{MANIFEST_KEY}", "-", check=True)
        previous = json.loads(out.stdout)
    except Exception:
        print("r2 sync: no previous manifest, full upload")

    changed = [rel for rel, digest in manifest.items() if previous.get(rel) != digest]
    removed = [rel for rel in previous if rel not in manifest]
    print(f"r2 sync: {len(changed)} changed/new, {len(removed)} removed")

    def upload(rel: str) -> None:
        aws("cp", str(files[rel]), f"s3://{bucket}/data/{rel}",
            "--content-type", "application/json")

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(upload, changed))
        list(pool.map(lambda rel: aws("rm", f"s3://{bucket}/data/{rel}"), removed))

    manifest_file = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "data-manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=1))
    aws("cp", str(manifest_file), f"s3://{bucket}/{MANIFEST_KEY}",
        "--content-type", "application/json")
    print("r2 sync: done")


if __name__ == "__main__":
    sys.exit(main())
