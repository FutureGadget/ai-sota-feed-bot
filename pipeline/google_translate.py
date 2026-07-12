"""Google Cloud Translation API v2 client for i18n translation.

Translates text fields using the Google Cloud Translation API Basic (v2).
Reads GOOGLE_TRANSLATE_API_KEY from the environment; no-ops when absent.

Uses only stdlib (urllib.request) — no new dependencies required.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

API_URL = "https://translation.googleapis.com/language/translate/v2"
ROOT = Path(__file__).resolve().parent.parent
GLOSSARY_PATH = ROOT / "config" / "glossary.yaml"

# Placeholder prefix used for notranslate protection
_NT_OPEN = '<span class="notranslate">'
_NT_CLOSE = "</span>"

# Max chars per API request (v2 limit is ~100K; stay well under)
_BATCH_CHAR_LIMIT = 50_000
_BATCH_ITEM_LIMIT = 128


# ---------------------------------------------------------------------------
# Glossary loading
# ---------------------------------------------------------------------------

_glossary_cache: list[str] | None = None


def _load_glossary() -> list[str]:
    """Load glossary terms, sorted longest-first for greedy matching."""
    global _glossary_cache
    if _glossary_cache is not None:
        return _glossary_cache
    if not GLOSSARY_PATH.exists():
        _glossary_cache = []
        return _glossary_cache
    data = yaml.safe_load(GLOSSARY_PATH.read_text(encoding="utf-8"))
    terms = data.get("terms") or []
    # Sort longest first so "Google DeepMind" matches before "Google"
    terms = sorted(terms, key=len, reverse=True)
    _glossary_cache = terms
    return _glossary_cache


def _build_glossary_pattern(terms: list[str]) -> re.Pattern | None:
    """Build a compiled regex that matches any glossary term as a whole word."""
    if not terms:
        return None
    escaped = [re.escape(t) for t in terms]
    # Word-boundary matching: use \b for terms that start/end with word chars
    parts = []
    for t, e in zip(terms, escaped):
        if t[0].isalnum() and t[-1].isalnum():
            parts.append(rf"\b{e}\b")
        elif t[0].isalnum():
            parts.append(rf"\b{e}")
        elif t[-1].isalnum():
            parts.append(rf"{e}\b")
        else:
            parts.append(e)
    return re.compile("|".join(parts))


def protect_terms(text: str) -> str:
    """Wrap glossary terms in notranslate spans to prevent translation."""
    terms = _load_glossary()
    pattern = _build_glossary_pattern(terms)
    if not pattern:
        return text

    def _wrap(m: re.Match) -> str:
        return f"{_NT_OPEN}{m.group(0)}{_NT_CLOSE}"

    return pattern.sub(_wrap, text)


def unprotect_terms(text: str) -> str:
    """Strip notranslate span wrappers from translated text."""
    return text.replace(_NT_OPEN, "").replace(_NT_CLOSE, "")


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------


def get_api_key() -> str | None:
    """Return the Google Translate API key from the environment, or None."""
    return os.environ.get("GOOGLE_TRANSLATE_API_KEY") or None


def translate_texts(
    texts: list[str],
    target: str,
    source: str = "en",
    *,
    api_key: str | None = None,
) -> list[str]:
    """Translate a list of strings via Google Cloud Translation API v2.

    Automatically protects glossary terms and handles batching.
    Returns the translated strings in the same order as input.

    If api_key is None, reads from GOOGLE_TRANSLATE_API_KEY env var.
    Raises ConnectionError if the API key is missing or the API call fails.
    """
    key = api_key or get_api_key()
    if not key:
        raise ConnectionError(
            "GOOGLE_TRANSLATE_API_KEY not set. "
            "Set it in the environment or pass api_key explicitly."
        )

    if not texts:
        return []

    import html

    # Escape HTML-sensitive characters (e.g. <, >, &) to prevent format:html interpretation issues,
    # then wrap glossary terms in notranslate spans.
    protected = [protect_terms(html.escape(t)) for t in texts]

    # Batch to stay under API limits
    results: list[str] = []
    batch: list[str] = []
    batch_chars = 0

    def _flush(batch_texts: list[str]) -> list[str]:
        return _call_api(batch_texts, target, source, key)

    for text in protected:
        text_len = len(text)
        if batch and (
            len(batch) >= _BATCH_ITEM_LIMIT
            or batch_chars + text_len > _BATCH_CHAR_LIMIT
        ):
            results.extend(_flush(batch))
            batch = []
            batch_chars = 0
        batch.append(text)
        batch_chars += text_len

    if batch:
        results.extend(_flush(batch))

    # Unprotect glossary terms from results
    return [unprotect_terms(t) for t in results]


def translate_text(
    text: str,
    target: str,
    source: str = "en",
    *,
    api_key: str | None = None,
) -> str:
    """Translate a single string. Convenience wrapper around translate_texts."""
    if not text or not text.strip():
        return text
    return translate_texts([text], target, source, api_key=api_key)[0]


def _call_api(
    texts: list[str],
    target: str,
    source: str,
    api_key: str,
) -> list[str]:
    """Make a single API call to Google Cloud Translation v2."""
    import time
    payload = json.dumps(
        {
            "q": texts,
            "target": target,
            "source": source,
            "format": "html",  # Required so notranslate spans are respected
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
        },
        method="POST",
    )

    max_attempts = 3
    body = None
    for attempt in range(1, max_attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                break
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            # Retry on 429 (rate limit) or 5xx (server errors)
            if (exc.code == 429 or exc.code >= 500) and attempt < max_attempts:
                sleep_sec = 2 ** attempt
                print(f"Google Translate API transient error {exc.code}, retrying in {sleep_sec}s... (Attempt {attempt}/{max_attempts})")
                time.sleep(sleep_sec)
                continue
            raise ConnectionError(
                f"Google Translate API Error (HTTP {exc.code}): {err_body}"
            ) from exc
        except urllib.error.URLError as exc:
            # DNS/Network issues
            if attempt < max_attempts:
                sleep_sec = 2 ** attempt
                print(f"Google Translate API network error: {exc.reason}, retrying in {sleep_sec}s... (Attempt {attempt}/{max_attempts})")
                time.sleep(sleep_sec)
                continue
            raise ConnectionError(
                f"Google Translate API connection failed: {exc.reason}"
            ) from exc
        except Exception as exc:
            raise ConnectionError(
                f"Google Translate API request failed: {exc}"
            ) from exc

    if not body:
        raise ConnectionError("Google Translate API request returned empty response")

    translations = body.get("data", {}).get("translations", [])
    if len(translations) != len(texts):
        raise ValueError(
            f"Expected {len(texts)} translations, got {len(translations)}"
        )

    results = []
    for t in translations:
        text = t.get("translatedText", "")
        # v2 returns HTML-encoded entities; decode them
        text = _decode_html_entities(text)
        results.append(text)
    return results


def _decode_html_entities(text: str) -> str:
    """Decode common HTML entities returned by the Translation API."""
    import html
    return html.unescape(text)


# ---------------------------------------------------------------------------
# Field-level translation helpers
# ---------------------------------------------------------------------------


def translate_fields(
    source: dict[str, Any],
    field_paths: list[str],
    target: str,
    source_lang: str = "en",
    *,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Translate specific fields in a dict, returning a new dict with translations.

    field_paths are dot-separated paths like:
      - "title"
      - "categories[].name"
      - "categories[].articles[].title"

    Only string leaf values are translated. The returned dict has the same
    structure as the source but contains only the translated fields.
    """
    # 1. Collect all string values to translate with their addresses
    entries: list[tuple[list[Any], str]] = []  # (address, value)
    for path in field_paths:
        _collect_strings(source, _parse_path(path), [], entries)

    if not entries:
        return {}

    # 2. Batch translate all collected strings
    texts = [v for _, v in entries]
    translated = translate_texts(texts, target, source_lang, api_key=api_key)

    # 3. Build the result dict by placing translated values at their addresses
    result: dict[str, Any] = {}
    for (address, _), trans_text in zip(entries, translated):
        _set_at_address(result, address, trans_text)

    return result


def _parse_path(path: str) -> list[str]:
    """Parse 'categories[].articles[].title' into ['categories', '[]', 'articles', '[]', 'title']."""
    segments: list[str] = []
    for part in path.split("."):
        if part.endswith("[]"):
            segments.append(part[:-2])
            segments.append("[]")
        else:
            segments.append(part)
    return segments


def _collect_strings(
    obj: Any,
    path_segments: list[str],
    address: list[Any],
    out: list[tuple[list[Any], str]],
) -> None:
    """Recursively collect string values at the given path."""
    if not path_segments:
        if isinstance(obj, str) and obj.strip():
            out.append((list(address), obj))
        return

    seg = path_segments[0]
    rest = path_segments[1:]

    if seg == "[]":
        # Current obj should be a list; iterate with index
        if not isinstance(obj, list):
            return
        for i, item in enumerate(obj):
            _collect_strings(item, rest, address + [i], out)
    else:
        # Navigate into dict key
        if not isinstance(obj, dict) or seg not in obj:
            return
        _collect_strings(obj[seg], rest, address + [seg], out)


def _set_at_address(root: dict[str, Any], address: list[Any], value: Any) -> None:
    """Set a value in a nested dict/list structure, creating containers as needed."""
    current: Any = root
    for i, key in enumerate(address[:-1]):
        next_key = address[i + 1]
        if isinstance(key, int):
            # Current is a list, navigate to index
            while len(current) <= key:
                current.append({} if isinstance(next_key, str) else [])
            current = current[key]
        else:
            # Current is a dict, navigate to key
            if key not in current:
                current[key] = [] if isinstance(next_key, int) else {}
            current = current[key]

    last_key = address[-1]
    if isinstance(last_key, int):
        while len(current) <= last_key:
            current.append(None)
        current[last_key] = value
    else:
        current[last_key] = value
