"""The source registry, split by who gathers each source.

- ``config/sources/fetched.yaml``: sources the collector fetches itself in the
  GitHub Action (RSS, sitemap, arXiv, OpenReview, Hugging Face, YouTube).
- ``config/sources/browsed.yaml``: sources a scheduled browsing routine gathers
  in a logged-in browser and commits under ``data/browsed/``. The collector
  reads those committed files; it never contacts the site.

Every reader of the registry goes through ``load_sources`` so the split stays
invisible to ranking, editorial, and the recap builders.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCES_DIR = ROOT / "config" / "sources"
REGISTRY_FILES = {
    "fetched": SOURCES_DIR / "fetched.yaml",
    "browsed": SOURCES_DIR / "browsed.yaml",
}
BROWSED_DATA_DIR = ROOT / "data" / "browsed"


def load_sources(kind: str | None = None, root: Path | None = None) -> list[dict[str, Any]]:
    """Return source entries from both registry files (or one ``kind``).

    Raises ``ValueError`` when a name appears twice, because every downstream
    map (slots, roles, health) is keyed by name.
    """
    sources_dir = (root / "config" / "sources") if root else SOURCES_DIR
    kinds = [kind] if kind else list(REGISTRY_FILES)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for k in kinds:
        path = sources_dir / REGISTRY_FILES[k].name
        if not path.exists():
            continue
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for src in payload.get("sources") or []:
            name = str(src.get("name") or "").strip()
            if name in seen:
                raise ValueError(f"duplicate_source_name:{name}")
            seen.add(name)
            out.append(src)
    return out


def registry_fingerprint() -> str:
    """Short hash over both registry files, for caches keyed on source config."""
    h = hashlib.sha256()
    found = False
    for path in REGISTRY_FILES.values():
        if path.exists():
            found = True
            h.update(path.read_bytes())
    return h.hexdigest()[:10] if found else "none"
