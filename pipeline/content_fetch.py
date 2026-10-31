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
        # A video's evidence path is the judge's transcript fetch, not the
        # watch-page HTML. Falling through here would attach the player JSON.
        if _is_video(it):
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


TRANSCRIPT_CACHE_FILE = ROOT / "data" / "quality" / "transcript_cache.json"
TRANSCRIPT_FAILURE_TTL_SECONDS = 6 * 3600


def _is_textual(text: str) -> bool:
    if len(text) < 100:
        return False
    printable = sum(1 for ch in text if ch.isprintable() or ch in "\n\t")
    return (printable / max(1, len(text))) >= 0.85


def _is_video(item: dict[str, Any]) -> bool:
    kind = str(item.get("type") or item.get("content_kind") or "").strip().lower()
    return kind == "video" or bool(item.get("video_id"))


def _load_transcript_cache() -> dict[str, Any]:
    if not TRANSCRIPT_CACHE_FILE.exists():
        return {}
    try:
        payload = json.loads(TRANSCRIPT_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _save_transcript_cache(cache: dict[str, Any]) -> None:
    TRANSCRIPT_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRANSCRIPT_CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _transcript_failure_is_fresh(record: Any) -> bool:
    if not isinstance(record, dict) or not record.get("error"):
        return False
    try:
        ts = datetime.fromisoformat(str(record.get("ts") or "").replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except Exception:
        return False
    age = (datetime.now(timezone.utc) - ts).total_seconds()
    return 0 <= age < TRANSCRIPT_FAILURE_TTL_SECONDS


def parse_transcript(raw: str, source_url: str = "") -> str:
    """Turn VTT, SRT, HTML, JSON, or plain text into one prose string.

    Buzzsprout publishes VTT with `<v SPEAKER_NN>` tags; other hosts publish
    SRT, HTML, or a JSON segment list. The judge only needs the words, so this
    drops cue timings, numeric SRT indices, and markup.
    """
    text = str(raw or "")
    lowered_url = str(source_url or "").lower()
    if lowered_url.endswith(".json") or text.lstrip().startswith(("{", "[")):
        try:
            payload = json.loads(text)
        except Exception:
            payload = None
        if payload is not None:
            segments = payload.get("segments") if isinstance(payload, dict) else payload
            if isinstance(segments, list):
                parts = []
                for segment in segments:
                    if isinstance(segment, dict):
                        parts.append(str(segment.get("body") or segment.get("text") or ""))
                    elif isinstance(segment, str):
                        parts.append(segment)
                text = " ".join(parts)
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.upper() == "WEBVTT":
            continue
        if stripped.startswith(("NOTE", "Kind:", "Language:")):
            continue
        if "-->" in stripped or re.fullmatch(r"\d+", stripped):
            continue
        lines.append(stripped)
    text = " ".join(lines)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def build_video_digest(description: str, transcript: str, max_chars: int = 2500) -> str:
    """Build a judge-sized digest of a long video transcript.

    A prefix would spend the budget on the intro, sponsor read, and guest bio.
    Instead keep the show notes (which state the episode's claims) and sample
    five windows at even intervals, snapped to word boundaries, away from the
    intro and outro where ads and sponsor reads live.
    """
    desc = _strip_html(str(description or ""))
    desc = re.sub(r"https?://\S+", " ", desc)
    desc = re.sub(r"\s+", " ", desc).strip()
    head = f"Show notes: {desc[:700]}" if desc else ""
    text = re.sub(r"\s+", " ", str(transcript or "")).strip()
    if not text:
        return head[:max_chars]
    if len(head) + len(text) + 12 <= max_chars:
        return f"{head} Transcript: {text}".strip()[:max_chars]

    budget = max(400, max_chars - len(head) - 40)
    windows = 5
    width = max(120, budget // windows)
    picks: list[str] = []
    for index in range(windows):
        position = int(len(text) * (index + 1) / (windows + 1))
        start = max(0, position - width // 2)
        end = min(len(text), start + width)
        if start > 0:
            next_space = text.find(" ", start)
            if 0 <= next_space < start + 80:
                start = next_space + 1
        if end < len(text):
            previous_space = text.rfind(" ", start, end)
            if previous_space > start + width // 2:
                end = previous_space
        chunk = text[start:end].strip()
        if chunk:
            picks.append(chunk)
    body = " \u2026 ".join(picks)
    return f"{head} Transcript (sampled): {body}".strip()[:max_chars]


def fetch_transcript_text(url: str, timeout: int = 10) -> str:
    """Fetch a published transcript URL and return parsed prose."""
    req = urllib.request.Request(
        _canon_url(url),
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) OpenClawFeedBot/1.0",
            "Accept": "text/vtt,application/x-subrip,application/json,text/html;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read(1_500_000).decode("utf-8", errors="ignore")
    return parse_transcript(raw, url)[:200_000]


def _should_fetch_paragraph(item: dict[str, Any]) -> bool:
    source = str(item.get("source") or "")
    url = str(item.get("url") or "")
    if _is_video(item):
        return False
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
    transcript_cache = _load_transcript_cache()
    out: dict[str, str] = {}
    started = time.monotonic()
    pending: list[str] = []
    video_pending: list[tuple[str, dict[str, Any], str]] = []

    for item in items[: max(1, int(top_n))]:
        url = _canon_url(item.get("url", ""))
        if not url:
            continue

        # A video's evidence is its transcript, not the watch page HTML. The
        # generic paragraph extractor returns ytInitialPlayerResponse JSON for
        # a YouTube page, which would be worse than no evidence at all.
        if _is_video(item):
            transcript_url = str(item.get("transcript_url") or "").strip()
            if not transcript_url:
                continue
            record = transcript_cache.get(transcript_url)
            if isinstance(record, dict) and str(record.get("text") or "").strip():
                text = str(record.get("text") or "")
                if _is_textual(text):
                    out[url] = text[:max_chars]
                continue
            if _transcript_failure_is_fresh(record):
                continue
            video_pending.append((url, item, transcript_url))
            continue

        if not _should_fetch_paragraph(item):
            continue
        existing = str(item.get("content_excerpt") or item.get("summary") or "").strip()
        if len(existing) >= 800:
            continue
        if url in cache and _is_textual(cache[url]):
            out[url] = cache[url][:max_chars]
            continue
        pending.append(url)

    def fetch_video(url: str, item: dict[str, Any], transcript_url: str) -> tuple[str, str, str, str | None]:
        try:
            text = fetch_transcript_text(transcript_url, timeout=timeout)
            if not text:
                return url, transcript_url, "", "empty_transcript"
            digest = build_video_digest(str(item.get("summary") or ""), text, max_chars)
            if not _is_textual(digest):
                return url, transcript_url, "", "unusable_transcript"
            return url, transcript_url, digest, None
        except Exception as exc:
            return url, transcript_url, "", str(exc)

    if video_pending:
        with ThreadPoolExecutor(max_workers=min(4, max(1, int(workers)))) as pool:
            futures = {}
            for url, item, transcript_url in video_pending:
                if time.monotonic() - started > max(1, int(time_budget_seconds)):
                    break
                futures[pool.submit(fetch_video, url, item, transcript_url)] = transcript_url
            for future in as_completed(futures):
                url, transcript_url, digest, error = future.result()
                now = datetime.now(timezone.utc).isoformat()
                if error:
                    transcript_cache[transcript_url] = {"error": error, "ts": now}
                    continue
                transcript_cache[transcript_url] = {"text": digest, "ts": now}
                out[url] = digest[:max_chars]
        _save_transcript_cache(transcript_cache)

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
