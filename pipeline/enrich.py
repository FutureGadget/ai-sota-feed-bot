from __future__ import annotations

import html
import re
from typing import Any

# Mechanical (no-LLM) item enrichment shared by the tier1 and tier0 builders.
# Tier-0 may re-process tier1 output (TIER0_INPUT=tier1), so everything here
# must stay idempotent.

GITHUB_RELEASE_URL_RE = re.compile(r"github\.com/[^/]+/([^/]+)/releases", re.I)
# Bare tag titles: "0.139.0", "v2.1.169", "0.32a3", "rust-v0.140.0-alpha.1"
BARE_VERSION_TITLE_RE = re.compile(r"^(?:[\w.]+-)?v?\d+[\w.\-+]*$", re.I)

_LI_RE = re.compile(r"<li[^>]*>(.*?)</li>", re.I | re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_SKIP_BULLET_RE = re.compile(
    r"^(bump |bumps |update[ds]? dependen|chore[(:\s]|full changelog|new contributors)", re.I
)


def github_repo_from_url(url: str) -> str:
    m = GITHUB_RELEASE_URL_RE.search(url or "")
    return m.group(1) if m else ""


def normalize_release_title(title: str, url: str) -> str:
    """Prefix bare version-tag titles (e.g. "0.139.0", "v2.1.169") with the
    repo name taken from the GitHub release URL."""
    t = (title or "").strip()
    if not BARE_VERSION_TITLE_RE.match(t):
        return t
    repo = github_repo_from_url(url)
    return f"{repo} {t}" if repo else t


def extract_release_highlights(summary_html: str, max_items: int = 3, max_chars: int = 160) -> list[str]:
    """Pull the first meaningful changelog bullets out of GitHub release notes HTML."""
    out: list[str] = []
    for m in _LI_RE.finditer(summary_html or ""):
        text = html.unescape(_TAG_RE.sub(" ", m.group(1)))
        text = re.sub(r"\s+by\s+@[\w\-\[\]]+(\s+in\s+\S+)?", "", text, flags=re.I)
        text = re.sub(r"https?://\S+", "", text)
        text = re.sub(r"\(\s*#?\d+\s*\)", "", text)
        text = re.sub(r"\s+", " ", text).strip(" .;:-")
        if not text or _SKIP_BULLET_RE.search(text):
            continue
        if len(text) > max_chars:
            text = text[: max_chars - 3].rstrip() + "..."
        out.append(text)
        if len(out) >= max_items:
            break
    return out


def clean_oneline(text: str, max_chars: int = 220) -> str:
    s = html.unescape(str(text or ""))
    s = _TAG_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > max_chars:
        s = s[: max_chars - 3].rstrip() + "..."
    return s


def summary_one_line(item: dict[str, Any], max_chars: int = 220) -> str:
    highlights = item.get("release_highlights") or []
    if highlights:
        return clean_oneline(" · ".join(highlights), max_chars)
    return clean_oneline(item.get("summary", "") or item.get("title", ""), max_chars)


def _canon_url(u: str) -> str:
    return (u or "").split("?")[0].strip().lower()


def record_duplicate(survivor: dict[str, Any], dup: dict[str, Any], max_entries: int = 4) -> None:
    """Track a deduped duplicate on the surviving item so the feed can show
    "also covered by" instead of silently dropping the extra coverage."""
    src = dup.get("source") or ""
    url = dup.get("url") or ""
    # Only cross-source duplicates count as coverage; same-source near-dups
    # are reposts, and arXiv cross-listings (same paper in cs.AI/cs.LG/cs.CL)
    # are category echoes.
    if src == survivor.get("source"):
        return
    if src.startswith("arxiv_") and str(survivor.get("source", "")).startswith("arxiv_"):
        return
    entries = survivor.setdefault("also_covered", [])
    candidates = [{"source": src, "url": url, "title": dup.get("title") or ""}]
    candidates += [e for e in (dup.get("also_covered") or []) if isinstance(e, dict)]
    seen = {(e.get("source"), _canon_url(e.get("url", ""))) for e in entries}
    seen.add((survivor.get("source"), _canon_url(survivor.get("url", ""))))
    for e in candidates:
        k = (e.get("source"), _canon_url(e.get("url", "")))
        if k in seen or e.get("source") == survivor.get("source") or len(entries) >= max_entries:
            continue
        seen.add(k)
        entries.append(
            {
                "source": str(e.get("source") or ""),
                "url": str(e.get("url") or ""),
                "title": str(e.get("title") or "")[:160],
            }
        )


def _looks_like_github_release(item: dict[str, Any]) -> bool:
    src = str(item.get("source", "")).lower()
    url = str(item.get("url", "")).lower()
    return "/releases/tag/" in url or src.endswith("_releases")


# hnrss.org wraps every item summary in a fixed metadata block — "Article URL",
# "Comments URL", "Points", "# Comments" — and link-only stories carry no other
# text, so once tags are stripped the summary is pure boilerplate. Strip those
# fields; if nothing else remains the title carries the item (Ask/Show HN text
# posts keep their body).
_HN_FIELD_RE = re.compile(
    r"(?:article url|comments url|points|#\s*comments)\s*:\s*\S*",
    re.I,
)


def _is_hackernews(item: dict[str, Any]) -> bool:
    src = str(item.get("source", "")).lower()
    url = str(item.get("url", "")).lower()
    return "hackernews" in src or "news.ycombinator.com" in url or "hnrss.org" in url


def strip_hn_boilerplate(summary_html: str) -> str:
    """Drop hnrss metadata; return remaining prose (or '' when there is none)."""
    text = clean_oneline(summary_html, max_chars=10_000)
    if not text:
        return ""
    residual = re.sub(r"\s+", " ", _HN_FIELD_RE.sub(" ", text)).strip()
    return residual


def enrich_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply mechanical enrichment in place (and return the list)."""
    for it in items:
        if _is_hackernews(it):
            it["summary"] = strip_hn_boilerplate(it.get("summary", ""))
        if not _looks_like_github_release(it):
            continue
        it["title"] = normalize_release_title(it.get("title", ""), it.get("url", ""))
        highlights = extract_release_highlights(it.get("summary", ""))
        if highlights:
            it["release_highlights"] = highlights
    return items
