from __future__ import annotations

import html
import json
import re
import urllib.request
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CACHE_FILE = ROOT / "data" / "llm" / "content_cache.json"
PARAGRAPH_CACHE_FILE = ROOT / "data" / "quality" / "content_cache.json"


def _canon_url(url: str) -> str:
    return (url or "").split("#")[0].strip()


def _strip_html(raw: str) -> str:
    s = re.sub(r"<script[\s\S]*?</script>", " ", raw, flags=re.I)
    s = re.sub(r"<style[\s\S]*?</style>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _load_cache() -> dict[str, Any]:
    if not CACHE_FILE.exists():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(cache: dict[str, Any]) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _fetch_text(url: str, timeout: int = 10, max_bytes: int = 800_000) -> str:
    req = urllib.request.Request(
        _canon_url(url),
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) OpenClawFeedBot/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read(max_bytes)
    try:
        txt = raw.decode("utf-8", errors="ignore")
    except Exception:
        txt = raw.decode(errors="ignore")
    return _strip_html(txt)


def build_content_map(
    items: list[dict[str, Any]],
    top_n: int = 30,
    excerpt_chars: int = 1200,
    timeout: int = 10,
    time_budget_seconds: int = 25,
) -> dict[str, str]:
    cache = _load_cache()
    out: dict[str, str] = {}
    started = time.monotonic()

    for it in items[:top_n]:
        if time.monotonic() - started > max(1, int(time_budget_seconds)):
            break
        u = _canon_url(it.get("url", ""))
        if not u:
            continue
        rec = cache.get(u)
        if isinstance(rec, dict) and rec.get("text"):
            out[u] = str(rec.get("text", ""))[:excerpt_chars]
            continue
        try:
            txt = _fetch_text(u, timeout=timeout)
            if txt:
                cache[u] = {"text": txt[:5000], "ts": datetime.now(timezone.utc).isoformat()}
                out[u] = txt[:excerpt_chars]
        except Exception:
            continue

    _save_cache(cache)
    return out


def _load_paragraph_cache() -> dict[str, str]:
    if not PARAGRAPH_CACHE_FILE.exists():
        return {}
    try:
        payload = json.loads(PARAGRAPH_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _save_paragraph_cache(cache: dict[str, str]) -> None:
    PARAGRAPH_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    PARAGRAPH_CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _is_textual(text: str) -> bool:
    if len(text) < 100:
        return False
    printable = sum(1 for ch in text if ch.isprintable() or ch in "\n\t")
    return (printable / max(1, len(text))) >= 0.85


def _should_fetch_paragraph(item: dict[str, Any]) -> bool:
    source = str(item.get("source") or "")
    url = str(item.get("url") or "")
    if source.startswith("search_") or "news.google.com" in url:
        return False
    if "/releases/tag/" in url or source.endswith("_releases"):
        return False
    if source.startswith("arxiv_") or "arxiv.org" in url:
        return False
    return True


def fetch_paragraph_text(url: str, timeout: int = 8, max_chars: int = 2500) -> str:
    """Extract article paragraphs, skipping navigation, tag clouds, and cookie bars."""
    req = urllib.request.Request(
        _canon_url(url),
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) OpenClawFeedBot/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read(800_000).decode("utf-8", errors="ignore")
    paragraphs = []
    for match in re.findall(r"<p\b[^>]*>(.*?)</p>", raw, re.I | re.S):
        text = re.sub(r"<[^>]+>", " ", match)
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) < 80:
            continue
        lowered = text.lower()
        if any(
            marker in lowered
            for marker in (
                "cookie",
                "subscribe to",
                "sign up for",
                "all rights reserved",
                "privacy policy",
                "skip to content",
                "follow us",
                "share this",
            )
        ):
            continue
        paragraphs.append(text)
        if sum(len(part) for part in paragraphs) >= max_chars:
            break
    text = " ".join(paragraphs)[:max_chars].strip()
    if len(text) < 300:
        return _strip_html(raw)[:max_chars]
    return text


def build_paragraph_map(
    items: list[dict[str, Any]],
    top_n: int = 160,
    max_chars: int = 2500,
    timeout: int = 8,
    workers: int = 8,
    time_budget_seconds: int = 120,
) -> dict[str, str]:
    """Fetch paragraph excerpts for judge candidates, cached by URL."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time

    cache = _load_paragraph_cache()
    out: dict[str, str] = {}
    started = time.monotonic()
    pending = []
    for item in items[: max(1, int(top_n))]:
        url = _canon_url(item.get("url", ""))
        if not url or not _should_fetch_paragraph(item):
            continue
        existing = str(item.get("content_excerpt") or item.get("summary") or "").strip()
        if len(existing) >= 800:
            continue
        if url in cache and _is_textual(cache[url]):
            out[url] = cache[url][:max_chars]
            continue
        pending.append(url)

    def fetch(url: str) -> tuple[str, str | None]:
        try:
            text = fetch_paragraph_text(url, timeout=timeout, max_chars=max_chars)
            return url, text if _is_textual(text) else None
        except Exception:
            return url, None

    with ThreadPoolExecutor(max_workers=max(1, int(workers))) as pool:
        futures = {}
        for url in pending:
            if time.monotonic() - started > max(1, int(time_budget_seconds)):
                break
            futures[pool.submit(fetch, url)] = url
        for future in as_completed(futures):
            url, text = future.result()
            if text:
                cache[url] = text
                out[url] = text[:max_chars]

    _save_paragraph_cache(cache)
    return out
