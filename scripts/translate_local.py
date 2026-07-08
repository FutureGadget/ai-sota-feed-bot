#!/usr/bin/env python3
"""Translate i18n candidates using a local LLM via LM Studio (OpenAI-compatible API).

Usage:
    # Translate all missing/stale daily pages for Korean:
    python scripts/translate_local.py --locale ko --surface daily

    # Translate a specific page:
    python scripts/translate_local.py --locale ko --surface daily --id 2026-07-05

    # Translate up to 5 candidates across all surfaces:
    python scripts/translate_local.py --locale ko --limit 5

    # Use a different model or endpoint:
    python scripts/translate_local.py --locale ko --surface daily \
        --model google/gemma-4-e4b \
        --base-url http://localhost:1234/v1

    # Dry run (show what would be translated without calling the LLM):
    python scripts/translate_local.py --locale ko --surface daily --dry-run

Prerequisites:
    - LM Studio running locally with the model loaded
    - Default endpoint: http://localhost:1234/v1
    - Default model: google/gemma-4-e4b
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Allow importing from pipeline/
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import export_i18n_candidates as exporter  # noqa: E402
import render_static_pages as render  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_BASE_URL = "http://localhost:1234/v1"
DEFAULT_MODEL = "google/gemma-4-e4b"
DEFAULT_LOCALE = "ko"

LOCALE_NAMES = {
    "ko": "Korean",
    "ja": "Japanese",
    "zh": "Chinese (Simplified)",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
}

# ---------------------------------------------------------------------------
# LM Studio client (OpenAI-compatible, no SDK dependency)
# ---------------------------------------------------------------------------

def _chat_completion(
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.3,
    max_tokens: int = 8192,
    timeout: int = 300,
) -> str:
    """Call the OpenAI-compatible chat/completions endpoint."""
    import urllib.request
    import urllib.error

    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        raise ConnectionError(f"LM Studio API Error (HTTP {exc.code}): {err_body}") from exc
    except Exception as exc:
        raise ConnectionError(
            f"Cannot reach LM Studio at {base_url}. "
            f"Is it running with the model loaded?\n  Error: {exc}"
        ) from exc

    choices = body.get("choices") or []
    if not choices:
        raise ValueError(f"Empty choices from LM Studio: {json.dumps(body, indent=2)}")
    return choices[0].get("message", {}).get("content", "")


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def _build_system_prompt(locale: str) -> str:
    lang = LOCALE_NAMES.get(locale, locale)
    return f"""You are a professional technical translator specializing in AI/ML content.
Translate the provided JSON fields from English to {lang}.

CRITICAL RULES:
1. Output ONLY a valid JSON object — no markdown fences, no commentary.
2. Translate ONLY the fields listed in "translate_these_fields". Copy everything else unchanged.
3. PRESERVE exactly as-is (do NOT translate):
   - URLs, source identifiers, dates, slugs, sids
   - Technical terms: model names (GPT-4, Claude, Gemini), company names (OpenAI, Anthropic, Google), product names
   - Acronyms widely used in their English form: RAG, MCP, RLHF, GPU, LLM, API, SDK, etc.
   - Code identifiers, benchmark names, percentages, prices
   - The JSON structure and all field names (keys)
4. Keep the same array order for categories, articles, bullets, etc.
5. Write natural, fluent {lang} — not word-by-word translation. Use the tone of a knowledgeable tech newsletter.
6. For article titles and summaries, keep them concise and informative.
"""


def _deep_merge(source: Any, translated: Any) -> Any:
    """Recursively merge translated fields on top of the original source."""
    if isinstance(source, dict) and isinstance(translated, dict):
        result = source.copy()
        for k, v in translated.items():
            if k in result:
                result[k] = _deep_merge(result[k], v)
            else:
                result[k] = v
        return result
    elif isinstance(source, list) and isinstance(translated, list):
        result = []
        for idx, item in enumerate(source):
            if idx < len(translated):
                result.append(_deep_merge(item, translated[idx]))
            else:
                result.append(item)
        return result
    else:
        return translated


def _filter_json(data: Any, paths: list[str]) -> Any:
    """Filter JSON to keep only paths that match the wildcard patterns."""
    parsed_paths = []
    for p in paths:
        segments = [s.replace("[]", "") for s in p.split(".")]
        parsed_paths.append(segments)
        
    def recurse(val: Any, prefix: list[str]) -> Any:
        if isinstance(val, dict):
            res = {}
            for k, v in val.items():
                current_prefix = prefix + [k]
                is_prefix = False
                is_exact = False
                for p in parsed_paths:
                    if p[:len(current_prefix)] == current_prefix:
                        is_prefix = True
                        if len(p) == len(current_prefix):
                            is_exact = True
                if is_prefix:
                    if is_exact:
                        res[k] = v
                    else:
                        res[k] = recurse(v, current_prefix)
            return res
        elif isinstance(val, list):
            return [recurse(item, prefix) for item in val]
        else:
            return val

    return recurse(data, [])


def _build_user_prompt(
    candidate: dict[str, Any],
    contract: dict[str, Any],
) -> str:
    source = candidate.get("source", {})
    surface = candidate["surface"]
    translated_fields = contract["translated_fields"]

    # Filter the source JSON to include ONLY fields that need translation
    filtered_source = _filter_json(source, translated_fields)

    return f"""Translate this {surface} page. The source JSON contains only the fields that need translation.

Rules:
1. Translate ONLY the values of the fields to the target language.
2. Do NOT translate or change any JSON keys.
3. Preserve the exact structure, list lengths, and list ordering.
4. Output only valid JSON.

Source JSON:
{json.dumps(filtered_source, ensure_ascii=False, indent=2)}
"""


# ---------------------------------------------------------------------------
# Response parsing and validation
# ---------------------------------------------------------------------------

def _repair_unescaped_quotes(text: str) -> str:
    """Escape unescaped double quotes inside JSON string values."""
    chars = list(text)
    n = len(chars)
    result = []
    inside_string = False
    
    i = 0
    while i < n:
        c = chars[i]
        
        if c == '"':
            # Check if this quote is escaped
            is_escaped = False
            k = i - 1
            while k >= 0 and chars[k] == '\\':
                is_escaped = not is_escaped
                k -= 1
                
            if is_escaped:
                result.append(c)
                i += 1
                continue
                
            if not inside_string:
                inside_string = True
                result.append(c)
                i += 1
            else:
                # Look ahead for next non-whitespace char
                next_non_ws = None
                j = i + 1
                while j < n:
                    if chars[j] not in (' ', '\t', '\n', '\r'):
                        next_non_ws = chars[j]
                        break
                    j += 1
                
                # If followed by a JSON structural separator, it's closing the string
                if next_non_ws in (',', '}', ']', ':'):
                    inside_string = False
                    result.append(c)
                else:
                    # Escape it
                    result.append('\\')
                    result.append('"')
                i += 1
        else:
            result.append(c)
            i += 1
            
    return "".join(result)


def _repair_json_escapes(text: str) -> str:
    """Escape backslashes that are not part of a valid JSON escape sequence."""
    pattern = r"\\(u[0-9a-fA-F]{4}|[\"\\/bfnrt]|.|$)"
    def repl(m):
        content = m.group(1)
        if content in ("\"", "\\", "/", "b", "f", "n", "r", "t") or (content.startswith("u") and len(content) == 5):
            return m.group(0)
        else:
            return "\\\\" + content
    return re.sub(pattern, repl, text)


def _extract_json(raw: str) -> dict[str, Any]:
    """Extract JSON from the LLM response, stripping markdown fences if present."""
    text = raw.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        # Remove opening fence (```json or ```)
        text = re.sub(r"^```\w*\n?", "", text, count=1)
        # Remove closing fence
        text = re.sub(r"\n?```\s*$", "", text, count=1)
    text = _repair_unescaped_quotes(text)
    text = _repair_json_escapes(text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"LLM returned invalid JSON:\n{raw[:500]}\n\nParse error: {exc}"
        ) from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"Expected a JSON object, got {type(parsed).__name__}")
    return parsed


def _validate_translation(
    translated: dict[str, Any],
    contract: dict[str, Any],
    surface: str,
) -> list[str]:
    """Perform basic schema validations on the translated JSON."""
    warnings = []
    # Ensure all target top-level keys exist
    for field_path in contract["translated_fields"]:
        top_key = field_path.split("[")[0].split(".")[0]
        if top_key not in translated:
            warnings.append(f"Missing translated field: {top_key}")

    # Basic content checks
    if surface in ("daily", "weekly"):
        cats = translated.get("categories", [])
        if not isinstance(cats, list) or len(cats) == 0:
            warnings.append("categories array is empty or missing")
        for i, cat in enumerate(cats):
            if not isinstance(cat, dict):
                continue
            if not cat.get("name"):
                warnings.append(f"categories[{i}].name is empty")
            articles = cat.get("articles", [])
            if not isinstance(articles, list) or len(articles) == 0:
                warnings.append(f"categories[{i}].articles is empty")

    return warnings


# ---------------------------------------------------------------------------
# Artifact assembly
# ---------------------------------------------------------------------------

def _assemble_artifact(
    candidate: dict[str, Any],
    translated: dict[str, Any],
    model_name: str,
) -> dict[str, Any]:
    """Build the final translation artifact JSON."""
    artifact: dict[str, Any] = {
        "locale": candidate["locale"],
        "source_path": candidate["source_path"],
        "source_hash": candidate["source_hash"],
        "translated_at": datetime.now(timezone.utc).isoformat(),
        "model": model_name,
        "review_status": "machine",
    }
    # Merge translated fields recursively on top of the original source
    merged = _deep_merge(candidate.get("source", {}), translated)
    artifact.update(merged)
    return artifact


# ---------------------------------------------------------------------------
# Main translation loop
# ---------------------------------------------------------------------------

def translate_candidates(
    *,
    locale: str,
    surfaces: set[str] | None,
    target_id: str | None,
    limit: int,
    base_url: str,
    model: str,
    dry_run: bool,
    temperature: float,
    timeout: int,
    include_fresh: bool,
    days: int | None = None,
) -> int:
    """Translate candidates and write artifact files. Return exit code."""
    # Build the candidate list via the existing exporter
    payload = exporter.build_export(
        locale=locale,
        surfaces=surfaces,
        include_fresh=include_fresh,
        include_source=True,  # We need the source to translate
        limit=limit if target_id is None else 500,
        days=days,
    )
    items = payload.get("items", [])

    # Filter to specific ID if requested
    if target_id is not None:
        items = [it for it in items if it["id"] == target_id]
        if not items:
            print(f"ERROR: No candidate found with id '{target_id}'", file=sys.stderr)
            return 1

    if not items:
        print("No candidates to translate (all fresh).")
        return 0

    print(f"Found {len(items)} candidate(s) to translate\n")

    if dry_run:
        print("DRY RUN — would translate:\n")
        for it in items:
            print(f"  [{it['status']:>7}] {it['surface']:>12} / {it['id']}")
            print(f"           {it['title'][:80]}")
        return 0

    # Check LM Studio connectivity first
    try:
        import urllib.request
        health_url = f"{base_url.rstrip('/')}/models"
        req = urllib.request.Request(health_url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            models_body = json.loads(resp.read().decode("utf-8"))
            available = [m.get("id", "") for m in models_body.get("data", [])]
            print(f"LM Studio connected. Available models: {', '.join(available)}")
            if model not in available:
                print(f"WARNING: Model '{model}' not in loaded models list. "
                      f"LM Studio may auto-select a loaded model.", file=sys.stderr)
    except Exception as exc:
        print(f"ERROR: Cannot reach LM Studio at {base_url}: {exc}", file=sys.stderr)
        return 1

    successes = 0
    failures = 0

    for i, candidate in enumerate(items, 1):
        surface = candidate["surface"]
        ident = candidate["id"]
        status = candidate["status"]
        contract = candidate["contract"]
        title = candidate.get("title", "")[:60]

        print(f"\n[{i}/{len(items)}] {surface}/{ident} ({status})")
        print(f"  Title: {title}")

        if not candidate.get("source"):
            print("  SKIP: No source data available")
            failures += 1
            continue

        # Build prompts
        system_prompt = _build_system_prompt(locale)
        user_prompt = _build_user_prompt(candidate, contract)

        # Call LM Studio
        print(f"  Translating via {model}...", end="", flush=True)
        start = time.monotonic()
        try:
            raw_response = _chat_completion(
                base_url,
                model,
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=8192,
                timeout=timeout,
            )
            elapsed = time.monotonic() - start
            print(f" done ({elapsed:.1f}s)")
        except Exception as exc:
            elapsed = time.monotonic() - start
            print(f" FAILED ({elapsed:.1f}s)")
            print(f"  Error: {exc}", file=sys.stderr)
            failures += 1
            continue

        # Parse and validate
        try:
            translated = _extract_json(raw_response)
        except ValueError as exc:
            print(f"  PARSE ERROR: {exc}", file=sys.stderr)
            # Save the raw response for debugging
            debug_path = ROOT / "data" / "i18n" / "_debug" / f"{surface}_{ident}.txt"
            debug_path.parent.mkdir(parents=True, exist_ok=True)
            debug_path.write_text(raw_response, encoding="utf-8")
            print(f"  Raw response saved to {debug_path}")
            failures += 1
            continue

        warnings = _validate_translation(translated, contract, surface)
        for w in warnings:
            print(f"  WARNING: {w}")

        # Assemble and write artifact
        artifact = _assemble_artifact(candidate, translated, model)
        artifact_path = ROOT / candidate["artifact_path"]
        artifact_path.parent.mkdir(parents=True, exist_ok=True)

        text = json.dumps(artifact, ensure_ascii=False, indent=2) + "\n"
        artifact_path.write_text(text, encoding="utf-8")
        print(f"  Written: {artifact_path.relative_to(ROOT)}")
        successes += 1

    print(f"\n{'='*50}")
    print(f"Done: {successes} translated, {failures} failed, {len(items)} total")

    return 0 if failures == 0 else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Translate i18n candidates using a local LLM via LM Studio.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--locale", default=DEFAULT_LOCALE,
        help=f"Target locale (default: {DEFAULT_LOCALE})",
    )
    parser.add_argument(
        "--surface", action="append",
        choices=sorted(exporter.SURFACE_ORDER),
        help="Limit to surface type; repeat for multiple (default: all)",
    )
    parser.add_argument(
        "--id", dest="target_id",
        help="Translate only the candidate with this exact id (date, slug, sid)",
    )
    parser.add_argument(
        "--limit", type=int, default=10,
        help="Max candidates to translate (default: 10)",
    )
    parser.add_argument(
        "--days", type=int,
        help="Limit candidates to those modified within N days from today",
    )
    parser.add_argument(
        "--include-fresh", action="store_true",
        help="Re-translate already fresh artifacts",
    )
    parser.add_argument(
        "--base-url", default=DEFAULT_BASE_URL,
        help=f"LM Studio API base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL,
        help=f"Model identifier (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--temperature", type=float, default=0.3,
        help="Sampling temperature (default: 0.3)",
    )
    parser.add_argument(
        "--timeout", type=int, default=300,
        help="Per-request timeout in seconds (default: 300)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show candidates without translating",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return translate_candidates(
        locale=args.locale,
        surfaces=set(args.surface or []) or None,
        target_id=args.target_id,
        limit=args.limit,
        base_url=args.base_url,
        model=args.model,
        dry_run=args.dry_run,
        temperature=args.temperature,
        timeout=args.timeout,
        include_fresh=args.include_fresh,
        days=args.days,
    )


if __name__ == "__main__":
    raise SystemExit(main())
