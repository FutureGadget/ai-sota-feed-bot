"""OpenRouter prices and serving metadata, independent of benchmark refreshes.

The catalog discovers models; endpoint responses supply complete provider offers.
Never combine prices from different endpoints or fall back to benchmark prices.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRICE_PATH = ROOT / "data/models/pricing.json"
RATE_KEYS = {
    "input": "prompt", "output": "completion", "cache_read": "input_cache_read",
    "cache_write": "input_cache_write", "cache_write_1h": "input_cache_write_1h",
}


def number(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        n = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return n if math.isfinite(n) and n >= 0 else None


def rates(raw):
    return {key: None if number(raw.get(field)) is None else round(number(raw[field]) * 1_000_000, 10)
            for key, field in RATE_KEYS.items()}


def identity(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def timestamp(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (AttributeError, ValueError, TypeError):
        return 0


def read_prices(path=PRICE_PATH):
    try:
        data = json.loads(path.read_text())
        return data if data.get("version") == 1 else {}
    except (OSError, ValueError, AttributeError):
        return {}


def normalize_offer(endpoint, author, checked_at):
    raw = endpoint.get("pricing") or {}
    normalized = rates(raw)
    if normalized["input"] is None or normalized["output"] is None:
        return None
    tag = str(endpoint.get("tag") or "")
    if not tag or not endpoint.get("provider_name"):
        return None
    # The published Google write field has an unresolved storage-time basis.
    # Keep the published value for audit, but never use it as a total write rate.
    write_basis = "replacement" if author in {"anthropic", "openai"} else "unverified"
    tiers = []
    for tier in raw.get("overrides") or []:
        threshold = number(tier.get("min_prompt_tokens"))
        if threshold is None:
            return None
        tiers.append({"min_prompt_tokens": threshold, "rates": rates({**raw, **tier})})
    return {
        "provider": endpoint["provider_name"], "tag": tag,
        "name": endpoint.get("name"), "rates": normalized,
        "write_basis": write_basis,
        "write_ttl": {"anthropic": "5 minutes", "openai": "30 minutes"}.get(author) if normalized["cache_write"] is not None else None,
        "quantization": endpoint.get("quantization"),
        "tiers": sorted(tiers, key=lambda t: t["min_prompt_tokens"]),
        "request_usd": number(raw.get("request")) or 0,
        "context_length": number(endpoint.get("context_length")),
        "max_output_tokens": number(endpoint.get("max_completion_tokens")),
        "supported_parameters": endpoint.get("supported_parameters") or [],
        "checked_at": checked_at,
    }


def select_offer(offers, preferred_tags):
    # Regional, flex and priority endpoints are distinct offers, not defaults.
    qualifiers = {"global", "fp4", "fp8", "bf16", "mxfp4", "nvfp4", "fp16", "int8", "int4", "zdr"}
    standard = [o for o in offers if set(o["tag"].split("/")[1:]) <= qualifiers]
    if not standard:
        return None
    def rank(offer):
        tag = offer["tag"]
        preference = next((i for i, preferred in enumerate(preferred_tags)
                           if tag == preferred or tag.startswith(preferred + "/")), len(preferred_tags))
        return preference, offer["rates"]["input"], offer["rates"]["output"], tag
    return min(standard, key=rank)


def refresh(previous, cfg, now, fetch_json, limit=None, priority=()):
    """Validate first, then replace each successful endpoint independently.

    `priority` ids (models the radar displays) refresh ahead of the rest of the
    catalog, so a displayed price cannot age past `stale_after_seconds` while
    the bounded batch works through models nobody sees.
    """
    checked = now.isoformat()
    result = copy.deepcopy(previous) if previous else {"version": 1, "models": {}}
    result.update(attempted_at=checked, error=None)
    try:
        rows = fetch_json(cfg["base_url"])["data"]
        if not isinstance(rows, list) or not rows:
            raise ValueError("empty catalog")
        models = {}
        for row in rows:
            model_id = row.get("id", "")
            if not re.fullmatch(r"[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+", model_id):
                continue
            if model_id in cfg.get("exclude_models", []) or model_id.startswith("openrouter/"):
                continue
            if "text" not in (row.get("architecture") or {}).get("output_modalities", []):
                continue
            models[model_id] = row
        if not models or (previous and len(models) < len(previous.get("models", {})) * .7):
            raise ValueError("catalog coverage regression")
    except (ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
        result["error"] = type(exc).__name__
        return result

    old_models = result["models"]
    result["models"] = {}
    due = []
    for model_id, row in models.items():
        old = old_models.get(model_id) or {}
        fingerprint = hashlib.sha256(json.dumps(row.get("pricing"), sort_keys=True).encode()).hexdigest()
        item = {**old, "id": model_id, "name": row.get("name") or model_id,
                "created": number(row.get("created")), "catalog_fingerprint": fingerprint}
        result["models"][model_id] = item
        age = now.timestamp() - timestamp(old.get("checked_at"))
        changed = old.get("fingerprint") != fingerprint or bool(old.get("error"))
        if changed or age >= cfg.get("endpoint_refresh_seconds", 14400):
            due.append((not changed, model_id not in priority, timestamp(old.get("checked_at")), -(item["created"] or 0), model_id))

    due.sort()
    targets = [entry[-1] for entry in due[:limit or cfg.get("max_endpoints_per_run", 32)]]
    def get_offers(model_id):
        item = result["models"][model_id]
        url = cfg["base_url"].rstrip("/") + "/" + model_id + "/endpoints"
        try:
            payload = fetch_json(url)["data"]
            if payload.get("id") != model_id or not isinstance(payload.get("endpoints"), list):
                raise ValueError("endpoint identity mismatch")
            offers = [normalize_offer(e, model_id.split("/")[0], checked)
                      for e in payload["endpoints"] if e.get("status") == 0]
            offers = [o for o in offers if o]
            if not offers:
                raise ValueError("no valid active offers")
            item.update(offers=offers, checked_at=checked, error=None, source_url=url,
                        fingerprint=item["catalog_fingerprint"])
        except (ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
            item["error"] = type(exc).__name__
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(get_offers, targets))
    result.update(catalog_checked_at=checked)
    return result


def match_models(rows, entries, source_cfg):
    """Catalog id per row, joined on exact names within an organization.

    Ambiguous or missing matches are None; never guessed.
    """
    org_aliases = source_cfg.get("organization_aliases", {})
    aliases = source_cfg.get("model_aliases", {})
    index = {}
    for model_id, item in entries.items():
        author, name = model_id.split("/", 1)
        org = org_aliases.get(author, author)
        for key in {identity(name), identity(item["name"].split(": ")[-1])}:
            index.setdefault((org, key), set()).add(model_id)
    matched = []
    for row in rows:
        explicit = aliases.get(row.get("url_slug"))
        matches = {explicit} if explicit in entries else set()
        if row.get("url_slug") not in aliases:
            for field in ("url_slug", "display_name"):
                matches.update(index.get((row.get("organization"), identity(row.get(field))), set()))
        matched.append(next(iter(matches)) if len(matches) == 1 else None)
    return matched


def apply_pricing(artifact, catalog, cfg, now=None):
    """Join on exact names within an organization; ambiguity stays unpriced."""
    now = now or datetime.now(timezone.utc)
    result = copy.deepcopy(artifact)
    rows = result.setdefault("models", [])
    source_cfg = cfg.get("sources", {}).get("openrouter", {})
    if not source_cfg.get("enabled", True):
        catalog = {}
    preferred = source_cfg.get("preferred_endpoints", {})
    entries = catalog.get("models", {})
    org_aliases = source_cfg.get("organization_aliases", {})
    joined = set()
    for row, model_id in zip(rows, match_models(rows, entries, source_cfg)):
        row["pricing_model_id"] = model_id
        if model_id:
            joined.add(model_id)

    # New releases can be discovered before AA evaluates them. No score is inferred.
    existing_slugs = {row.get("url_slug") for row in rows}
    for model_id, item in entries.items():
        if model_id in joined or not item.get("created"):
            continue
        if now.timestamp() - item["created"] > cfg.get("recency_days", 90) * 86400:
            continue
        author, name = model_id.split("/", 1)
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        if slug in existing_slugs:
            continue
        existing_slugs.add(slug)
        rows.append({"url_slug": slug, "base_slug": identity(name), "slug": identity(name),
                     "name": item["name"].split(": ")[-1], "display_name": item["name"].split(": ")[-1],
                     "organization": org_aliases.get(author, author), "variant_label": None,
                     "release_date": None, "catalog_added_at": datetime.fromtimestamp(item["created"], timezone.utc).isoformat(),
                     "joined_sources": ["openrouter"], "pricing_model_id": model_id})

    for row in rows:
        model_id = row.get("pricing_model_id")
        item = entries.get(model_id) or {}
        author = (model_id or "").split("/")[0]
        offer = select_offer(item.get("offers", []), preferred.get(author, [author]))
        row["pricing"] = None
        for field in ("price_input_per_1m", "price_output_per_1m", "price_blended_per_1m"):
            row[field] = None
        if offer:
            stale = now.timestamp() - timestamp(offer.get("checked_at")) > source_cfg.get("stale_after_seconds", 86400)
            row["pricing"] = {**offer, "model_id": model_id, "source_url": item["source_url"],
                              "stale": stale, "refresh_error": item.get("error")}
            if not stale:
                p = offer["rates"]
                row.update(price_input_per_1m=p["input"], price_output_per_1m=p["output"],
                           price_blended_per_1m=(3 * p["input"] + p["output"]) / 4)
    result.setdefault("sources", {})["openrouter"] = {
        "available": any(row.get("pricing") for row in rows),
        "attribution": "OpenRouter - provider endpoint prices in USD",
        "url": source_cfg.get("base_url", "https://openrouter.ai/api/v1/models"),
        "catalog_checked_at": catalog.get("catalog_checked_at"),
        "attempted_at": catalog.get("attempted_at"), "error": catalog.get("error"),
    }
    # Recompute both token frontiers with the same prices shipped to the page.
    if __package__:
        from .collect_models import compute_frontier
    else:
        from collect_models import compute_frontier
    frontier = compute_frontier(rows, cfg.get("frontier_metrics"), cfg.get("frontier_dominated_by_cap", 5))
    for row in rows:
        row["frontier"] = frontier.get(row.get("url_slug"), {})
    return result


def radar_model_ids(catalog, cfg):
    """Catalog ids the radar shows: rows of data/models/latest.json that join."""
    try:
        rows = json.loads((PRICE_PATH.parent / "latest.json").read_text()).get("models", [])
    except (OSError, ValueError, AttributeError):
        return set()
    return {mid for mid in match_models(rows, catalog.get("models", {}), cfg) if mid}


def main():
    import requests
    from collect_models import load_config
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--max-endpoints", type=int, help="override the bounded endpoint refresh batch")
    args = parser.parse_args()
    cfg = load_config()["sources"]["openrouter"]
    if not cfg.get("enabled", True):
        return 0
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    def fetch_json(url):
        try:
            response = requests.get(url, headers=headers, timeout=20)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise OSError(type(exc).__name__) from exc
    previous = read_prices()
    result = refresh(previous, cfg, datetime.now(timezone.utc), fetch_json, args.max_endpoints,
                     radar_model_ids(previous, cfg))
    PRICE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = PRICE_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(PRICE_PATH)
    failures = sum(bool(m.get("error")) for m in result.get("models", {}).values())
    print(f"model_prices models={len(result.get('models', {}))} failed_endpoints={failures} catalog_error={result.get('error')}")
    return 1 if result.get("error") else 0


if __name__ == "__main__":
    raise SystemExit(main())
