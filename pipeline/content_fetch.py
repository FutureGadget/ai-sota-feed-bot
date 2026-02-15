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
