#!/usr/bin/env python3
"""Translate the home feed's cards into the per-card store.

One ``translator.Job`` per card, each card translated once into the store
(``data/i18n/<locale>/feed/cards.json``, see ``card_store``). The store covers
the cards the English home's default request returns; ``/api/feed?locale=<l>``
overlays them onto the live English cards. Spend is metered in USD by the shared
``translator.Ledger``; when the monthly cap is reached the store keeps what was
translated and the run ends normally. Untranslated cards stay English.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    from . import card_store, locales, translator
except ImportError:
    import card_store
    import locales
    import translator

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ("title", "summary_1line", "why_it_matters")
MAX_TRANSLATIONS = 60

def _norm_url(url: str | None) -> str:
    s = str(url or "").strip()
    return s[:-1] if s.endswith("/") and len(s) > 1 else s

def _clean_text(v: Any) -> str:
    if not v:
        return ""
    return " ".join(str(v).split())

def _translation_key(it: dict[str, Any]) -> str:
    url = _norm_url(it.get("url"))
    return url or str(it.get("id") or it.get("title") or "").strip()

def _source_hash(it: dict[str, Any]) -> str:
    also_covered = it.get("also_covered")
    if not isinstance(also_covered, list):
        also_covered = []

    ac_payload = []
    for entry in also_covered:
        if not isinstance(entry, dict):
            continue
        title = _clean_text(entry.get("title"))
        url = _norm_url(entry.get("url"))
        if url or title:
            ac_payload.append({"title": title, "url": url})

    payload = {
        "also_covered": ac_payload,
        "summary_1line": _clean_text(it.get("summary_1line")),
        "title": _clean_text(it.get("title")),
        "why_it_matters": _clean_text(it.get("why_it_matters")),
    }

    j = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(j.encode('utf-8')).hexdigest()

# The English home's default view (web/index.html buildFeedUrl): the Brief lens,
# a rolling 24-hour window keyed by feed arrival, up to 200 cards.
HOME_LABEL = "brief"
HOME_LIMIT = 200
HOME_HOURS = 24

_FETCH_JS = """
import { GET } from './api/feed.js';
const url = new URL('http://localhost/api/feed');
for (const [key, value] of Object.entries(JSON.parse(process.env.FEED_PARAMS))) {
  url.searchParams.set(key, value);
}
GET({ url: url.toString() })
  .then((res) => res.json())
  .then((data) => { console.log(JSON.stringify(data)); })
  .catch((err) => { console.error(err); process.exit(1); });
"""


def home_params(now: datetime) -> dict[str, str]:
    """/api/feed params of the English home's default request."""
    def fmt(d: datetime) -> str:
        return d.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    return {
        "label": HOME_LABEL,
        "limit": str(HOME_LIMIT),
        "window": "arrival",
        "from": fmt(now - timedelta(hours=HOME_HOURS)),
        "to": fmt(now),
    }


def _fetch_english_feed(params: dict[str, str]) -> dict[str, Any]:
    """The English /api/feed response for ``params``, from the repo's own handler."""
    env = {**os.environ, "FEED_PARAMS": json.dumps(params)}
    res = subprocess.run(
        ["node", "-e", _FETCH_JS], cwd=ROOT, env=env, capture_output=True, text=True, check=True
    )
    return json.loads(res.stdout)


def item_job(it: dict[str, Any]) -> translator.Job:
    """The translation job for one feed card: its visible text, with the article excerpt as context."""
    fields = {f: it[f] for f in FIELDS if (it.get(f) or "").strip()}
    for i, entry in enumerate(it.get("also_covered") or []):
        if isinstance(entry, dict) and (entry.get("title") or "").strip():
            fields[f"also_covered_title_{i}"] = entry["title"]
    context = it.get("content_excerpt") or it.get("summary") or ""
    return translator.Job(_translation_key(it), fields, context)


def _card_entry(
    it: dict[str, Any], result: translator.Result, model: str, now: datetime
) -> card_store.CardEntry:
    """The store entry for one freshly translated English card."""
    return {
        "source_hash": _source_hash(it),
        "model": model,
        "translated_at": now.isoformat(),
        "last_seen": now.isoformat(),
        **{f: result.fields.get(f) or it.get(f) or "" for f in FIELDS},
        "also_covered": [
            {"url": entry.get("url"), "title": result.fields.get(f"also_covered_title_{i}", entry.get("title"))}
            for i, entry in enumerate(it.get("also_covered") or [])
        ],
    }


def _unique(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The cards in order, each translation key once."""
    seen: set[str] = set()
    out = []
    for it in items:
        key = _translation_key(it)
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out


def main(client=None):
    parser = argparse.ArgumentParser(description="Translate the home feed's cards into the per-card store.")
    parser.add_argument("--locale", default="ko", choices=locales.others(locales.DEFAULT))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    store_path = card_store.store_path(ROOT, args.locale)

    now = datetime.now(timezone.utc)
    model = translator.model_for("feed")
    ledger = translator.Ledger(ROOT / "data" / "i18n" / "translation_spend.json", now=lambda: now)
    print(f"localized_feed_budget usd_spent={ledger.spent:.4f} cap={ledger.monthly_cap:.2f} month={now:%Y-%m}")

    store = card_store.load(store_path, args.locale)

    print(f"Fetching the English home's default feed (label={HOME_LABEL}, limit={HOME_LIMIT})...")
    wanted = _unique(_fetch_english_feed(home_params(now)).get("items", []))
    if not wanted:
        print("No items in feed!")
        return

    dirty = [
        it for it in wanted
        if not card_store.is_fresh(store["cards"].get(_translation_key(it)), _source_hash(it), model)
    ]
    to_translate = dirty[:MAX_TRANSLATIONS]

    if args.dry_run:
        print(f"\nDRY RUN: {len(wanted)} cards on the English home.")
        print(f"  Already translated: {len(wanted) - len(dirty)}")
        print(f"  Would translate: {len(to_translate)} of {len(dirty)} untranslated (max {MAX_TRANSLATIONS} per run)")
        return

    # Translate one card per call, so a card that fails does not discard the others.
    translated = 0

    if to_translate:
        print(f"Translating up to {len(to_translate)} items (max {MAX_TRANSLATIONS})...")
        try:
            client = client or translator.make_client()
        except Exception as exc:
            print(f" Cannot create the Anthropic client: {exc}", file=sys.stderr)
            to_translate = []
        for it in to_translate:
            try:
                (result,) = translator.translate(
                    [item_job(it)], args.locale, "feed", client=client, ledger=ledger
                )
            except translator.BudgetExceeded as exc:
                # Keep the cards translated so far; the cap resets with the ledger month.
                print(f"localized_feed_budget_cap_reached: {exc}", file=sys.stderr)
                break
            except translator.TranslationError as exc:
                print(f" Translation FAILED: {exc}", file=sys.stderr)
                continue
            except Exception as exc:
                print(f" Translation FAILED, stopping: {exc}", file=sys.stderr)
                break
            store["cards"][_translation_key(it)] = _card_entry(it, result, model, now)
            translated += 1
        print(f" Translated {translated} items.")
    else:
        print("All wanted cards are already translated.")

    for it in wanted:
        entry = store["cards"].get(_translation_key(it))
        if entry:
            entry["last_seen"] = now.isoformat()
    pruned = card_store.prune(store, now)
    card_store.save(store_path, store, now)
    print(f"Wrote {len(store['cards'])} cards to {store_path.relative_to(ROOT)} (pruned {pruned})")


if __name__ == "__main__":
    main()
