"""Deterministic release significance for the served feed.

The Jev ``release_lane`` question is binary and written for the default Brief:
it treats every release-role item as a Releases-tab candidate. That is right
for a bare version bump and wrong for a release with a substantive changelog,
so vLLM's minor release once scored 0.03 next to ``codex 0.165.0-alpha.1``.

This module supplies the missing distinction. It is deliberately rule-based:
release feeds are structured, and deciding whether a release is a version bump
or a real change is not a semantic judgment call.

Tiers:
- ``major``: a substantive changelog, a first-party open-weight model drop, or
  a stable X.0.0 version bump. Brief-eligible.
- ``minor``: a bare version bump, a dependency update, a prerelease, or a
  generic "bug fixes" note. Releases tab only.

The ranking adds a bounded Stage C term for ``major`` releases so they rank
above minor bumps inside their own slot. The slot's ``max_items`` and
``max_per_source`` still cap how many releases reach the edition.
"""

from __future__ import annotations

import re
from typing import Any

# A version with a prerelease suffix ("0.165.0-alpha.1", "v0.32.1rc0") is not
# Brief-ready even when the changelog is substantive.
_PRERELEASE_RE = re.compile(
    r"\b\d+\.\d+(?:\.\d+)?(?:[-.]?(?:alpha|beta|rc|pre|preview|dev|nightly|canary|snapshot)\d*)\b",
    re.I,
)
_PRERELEASE_WORD_RE = re.compile(
    r"\b(?:alpha|beta|rc|pre|preview|dev|nightly|canary|snapshot)\b",
    re.I,
)
_VERSION_RE = re.compile(
    r"\b(?:v|rust-v|release[- ])?(\d+)\.(\d+)(?:\.(\d+))?(?:\.\d+)?\b",
    re.I,
)
_HF_SOURCE_RE = re.compile(r"^hf_[a-z0-9_]+_releases$", re.I)
_HF_TITLE_RE = re.compile(r"released on hugging face", re.I)

# Highlights that carry no standalone engineering signal. The first group is
# version/dependency boilerplate; the second is the generic release-note
# vocabulary that the web release row already suppresses for display.
_GENERIC_HIGHLIGHT_RE = re.compile(
    r"^(?:"
    r"bump(?:s|ed)?\b|"
    r"chore\b|"
    r"ci[:\s]|"
    r"clarif\w*\b|"
    r"document(?:ation|s|ed)?\b|"
    r"docs?\b|"
    r"readme\b|"
    r"typos?\b|"
    r"tests?\b|"
    r"lint\b|"
    r"refactor\b|"
    r"update[ds]? (?:the )?(?:bundled|dependenc|dependency|deps)\b|"
    r"updated? (?:the )?bundled\b|"
    r"updated? (?:the )?(?:readme|docs?|documentation)\b|"
    r"updated? .* to version\b|"
    r"release(?:\([^)]*\))?[:\s]|"
    r"version(?:s)?\b|"
    r"v?\d+(?:\.\d+)+(?:[-.][a-z0-9]+)*$|"
    r"bug fixes?\b|"
    r"minor (?:fixes|changes|updates)\b|"
    r"performance improvements?\b|"
    r"stability improvements?\b|"
    r"maintenance\b|"
    r"various fixes\b|"
    r"no release notes\b|"
    r"full changelog\b|"
    r"new contributors\b|"
    r"see (?:the )?(?:full )?changelog\b"
    r")",
    re.I,
)

# Strong action words and technical nouns. Weak nouns such as cli/sdk/api/tool
# are deliberately absent: "CLI emits..." and "updated bundled CLI" are not
# release significance on their own, and they made docs/CI bullets look major.
_ACTION_RE = re.compile(
    r"\b(?:add|added|adds|adding|fix|fixed|fixes|fixing|support|supports|supported|"
    r"introduc|new|endpoint|cache|kernel|performance|latency|throughput|"
    r"security|breaking|deprecat|remove|improve|parallel|memory|quantiz|"
    r"serving|inference|auth|gateway|monitor|namespace|recursion|"
    r"stream|protocol|parser|scheduler|migration|"
    r"crash|bug|error|timeout|retry|proxy|reasoning|context|embedding|token|"
    r"benchmark|eval|evaluation|deploy|scaling|gpu|nvfp4|kv)\b",
    re.I,
)


def is_release_item(item: dict[str, Any]) -> bool:
    """True for any item that the Releases tab owns a lane for."""
    if not isinstance(item, dict):
        return False
    if str(item.get("source_role") or "").strip().lower() == "release":
        return True
    if str(item.get("type") or "").strip().lower() == "release":
        return True
    if str(item.get("llm_category") or "").strip().lower() == "release":
        return True
    source = str(item.get("source") or "").strip().lower()
    return source.startswith("hf_") or source.endswith("_releases")


def _squash(text: Any) -> str:
    return " ".join(str(text or "").split()).strip(" .;:-")


def _highlight_is_substantive(text: str) -> bool:
    """A changelog bullet with a real feature/fix, not a version or dependency note."""
    t = _squash(text)
    if len(t) < 30:
        return False
    if _GENERIC_HIGHLIGHT_RE.search(t):
        return False
    if not re.search(r"[A-Za-z]{3,}", t):
        return False
    return bool(_ACTION_RE.search(t))


def _has_substantive_highlights(item: dict[str, Any]) -> bool:
    highlights = item.get("release_highlights") or []
    return any(_highlight_is_substantive(str(h)) for h in highlights if str(h).strip())


def _is_prerelease(item: dict[str, Any]) -> bool:
    # The release's own version lives in the title (enrich.normalize_release_title
    # prefixes bare tags). Checking the summary would mark a stable release
    # minor whenever its changelog happens to mention a dependency beta.
    title = str(item.get("title") or "")
    if _PRERELEASE_RE.search(title):
        return True
    return bool(_PRERELEASE_WORD_RE.search(title) and _VERSION_RE.search(title))


def _version_parts(item: dict[str, Any]) -> tuple[int, int, int] | None:
    for field in ("title", "summary"):
        match = _VERSION_RE.search(str(item.get(field) or ""))
        if not match:
            continue
        try:
            major = int(match.group(1))
            minor = int(match.group(2))
            patch = int(match.group(3) or 0)
        except (TypeError, ValueError):
            continue
        return major, minor, patch
    return None


def classify_release_tier(item: dict[str, Any]) -> str | None:
    """Return ``major``, ``minor``, or ``None`` for non-release items.

    ``major`` means Brief-eligible. The caller still applies the normal judge
    headroom bar to non-release items; this tier only decides whether the
    release lane may show the item in the default Brief.
    """
    if not is_release_item(item):
        return None

    title = str(item.get("title") or "")
    source = str(item.get("source") or "")
    if _HF_SOURCE_RE.match(source) or _HF_TITLE_RE.search(title):
        # A first-party open-weight drop is a launch signal, not a changelog.
        return "major"

    if _is_prerelease(item):
        return "minor"

    if _has_substantive_highlights(item):
        return "major"

    parts = _version_parts(item)
    if parts and parts[0] >= 1 and parts[1] == 0 and parts[2] == 0:
        return "major"

    return "minor"
