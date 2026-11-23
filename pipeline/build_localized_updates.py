#!/usr/bin/env python3
"""Translate the Editor's Desk items into the per-item store.

The desk (the "Latest from the Editor's Desk" strip and the updates panels) lists
the editorial catalog that ``/api/updates`` serves: recap, storyline, topic,
foundation and playbook items, each with a title and a one-line summary. The
store, ``data/i18n/<locale>/updates/titles.json``, holds one entry per catalog
item with both fields in the reader's language. ``/api/updates?locale=<l>``
overlays an entry while its ``source_hash`` still equals the item's English text.
The store's ``links`` map sends a desk link to the reader's language: catalog item
id to the localized path of its page, for every item whose page exists in that
language under ``web/``. It is independent of the text, so an item still shown
in English links its Korean page when there is one.

Each text comes from the first source that has it:

1. A current Korean artifact of the same page (recap, storyline, topic,
   foundation, playbook), found by its own ``source_hash``. Free.
2. The entry the last run stored for the same English text. Free.
3. One ``translator.translate`` call per item, for the newest items of each
   section only, at most ``MAX_TRANSLATIONS`` per run. Spend is metered in USD by
   the shared ``translator.Ledger``; at the monthly cap the run keeps what it has
   and ends normally.

An item with a missing field gets no entry and stays English.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

try:
    from . import locales, render_static_pages as render, translator
except ImportError:
    import locales
    import render_static_pages as render
    import translator

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ("title", "summary")
MAX_TRANSLATIONS = 24
# The desk shows the newest items of each section (the strip and "Latest updates"
# take the top three overall, each section panel the top three of its section),
# so only these are worth paying to translate.
DESK_PER_SECTION = 6
SUMMARY_MAX_CHARS = 240  # the cut in excerpt() of lib/editorial-catalog.js

# Catalog section -> the page surface whose Korean artifact may hold its text.
SECTION_SURFACE = {
    "daily": "daily",
    "weekly": "weekly",
    "playbook": "playbook",
    "storylines": "storyline",
    "map": "topic",
    "foundations": "foundations",
}

_CATALOG_JS = """
import { buildEditorialCatalog } from './lib/editorial-catalog.js';
console.log(JSON.stringify(buildEditorialCatalog('data')));
"""


class Entry(TypedDict):
    source_hash: str
    translated_at: str
    title: str
    summary: str
    # Where each field came from: "artifact" or the translator model.
    origin: dict[str, str]


Texts = dict[str, str]


def clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def source_hash(item: dict[str, Any]) -> str:
    """Hash of an item's English display text; the same payload as ``updateHash`` in
    lib/update-translations.js (tests/test_updates_hash_parity.py pins them)."""
    payload = {"summary": clean(item.get("summary")), "title": clean(item.get("title"))}
    text = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def store_path(root: Path, locale: str) -> Path:
    return root / "data" / "i18n" / locale / "updates" / "titles.json"


def load_store(path: Path) -> dict[str, Entry]:
    """The stored entries by catalog item id; empty when the file is missing or unreadable."""
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    items = raw.get("items") if isinstance(raw, dict) else None
    return items if isinstance(items, dict) else {}


def load_links(path: Path) -> dict[str, str]:
    """The stored ``links`` map; empty when the file is missing or unreadable."""
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    links = raw.get("links") if isinstance(raw, dict) else None
    return links if isinstance(links, dict) else {}


def localized_links(catalog: list[dict[str, Any]], locale: str, root: Path) -> dict[str, str]:
    """Catalog item id -> the item's page in ``locale``, for the pages rendered there."""
    prefix = locales.get(locale).path_prefix
    web = root / "web" / prefix.strip("/")
    links = {}
    for item in catalog:
        href = str(item.get("href") or "")
        if href.startswith("/") and (web / f"{href.strip('/')}.html").is_file():
            links[str(item["id"])] = f"{prefix}{href}"
    return dict(sorted(links.items()))


def save_store(path: Path, locale: str, items: dict[str, Entry], links: dict[str, str], now: datetime) -> None:
    out = {"locale": locale, "updated_at": now.isoformat(), "items": dict(sorted(items.items())), "links": links}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _fetch_catalog() -> list[dict[str, Any]]:
    """The English editorial catalog, from the repo's own builder (what /api/updates serves)."""
    res = subprocess.run(
        ["node", "--input-type=module", "-e", _CATALOG_JS],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    return json.loads(res.stdout)


# --- Korean artifacts ---------------------------------------------------------

def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


class EnglishSources:
    """The English page behind a catalog item, the object its artifact's hash is of."""

    def __init__(self, root: Path):
        self._data = root / "data"
        self._indexes: dict[str, Any] = {}

    def _index(self, name: str) -> dict:
        if name not in self._indexes:
            loaded = _load_json(self._data / name / "index.json")
            self._indexes[name] = loaded if isinstance(loaded, dict) else {}
        return self._indexes[name]

    def get(self, surface: str, ident: str) -> dict | None:
        if surface in ("daily", "weekly", "playbook"):
            source = _load_json(self._data / surface / f"{ident}.json")
        elif surface == "storyline":
            source = _load_json(self._data / "storylines" / f"{ident}.json")
        elif surface == "topic":
            source = (self._index("wiki").get("nodes") or {}).get(ident)
        else:
            source = (self._index("foundations").get("concepts") or {}).get(ident)
        return source if isinstance(source, dict) else None


def _excerpt(value: Any) -> str:
    """The catalog's ``excerpt()`` for a summary: links and markup stripped, 240 characters."""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean(value)).replace("*", "").replace("`", "")
    if len(text) <= SUMMARY_MAX_CHARS:
        return text
    return re.sub(r"\s+\S*$", "", text[: SUMMARY_MAX_CHARS - 3]) + "…"


def _first(value: Any) -> Any:
    return (value[0] if value else "") if isinstance(value, list) else value


def _artifact_summary(surface: str, artifact: dict, source: dict) -> str:
    """The artifact's text for the field the catalog uses as an item's summary.

    Only where the catalog's choice is mirrored exactly; every other surface
    leaves the summary to the translator.
    """
    if surface in ("daily", "weekly", "playbook"):
        return _excerpt(_first(artifact.get("highlights")) or _first(artifact.get("intro")))
    if surface == "storyline":
        editorial, ko = source.get("editorial") or {}, artifact.get("editorial") or {}
        if editorial.get("stale"):
            return ""
        field = "whats_new" if editorial.get("whats_new") else "tldr" if editorial.get("tldr") else ""
        return _excerpt(ko.get(field)) if field else ""
    return ""


def artifact_texts(
    item: dict[str, Any], locale: str, root: Path, sources: EnglishSources
) -> Texts:
    """The fields a current Korean artifact of this item's page can supply.

    An artifact text that equals the English (a storyline label left in English)
    is no translation, so it does not count.
    """
    section, _, key = str(item["id"]).partition(":")
    surface = SECTION_SURFACE.get(section)
    if not surface or key.startswith("lab:"):
        return {}
    artifact = _load_json(root / "data" / "i18n" / locale / surface / f"{key}.json")
    source = sources.get(surface, key)
    if not isinstance(artifact, dict) or not source:
        return {}
    if not render.i18n_hash_matches(artifact.get("source_hash"), source):
        return {}
    found = {
        "title": clean(artifact.get("title") or artifact.get("label")),
        "summary": _artifact_summary(surface, artifact, source),
    }
    return {f: text for f, text in found.items() if text and text != clean(item.get(f))}


# --- Translation --------------------------------------------------------------

def wanted_fields(item: dict[str, Any]) -> list[str]:
    """The display fields an item has in English."""
    return [f for f in FIELDS if clean(item.get(f))]


def item_job(item: dict[str, Any], fields: list[str]) -> translator.Job:
    """The translation job for the fields of one item still missing, with its summary as context."""
    context = f"Editor's Desk {item.get('section_label') or 'item'}. {clean(item.get('summary'))}"
    return translator.Job(str(item["id"]), {f: clean(item[f]) for f in fields}, context)


def desk_window(items: list[dict[str, Any]]) -> set[str]:
    """Ids of the newest ``DESK_PER_SECTION`` items of each section (``items`` is newest first)."""
    seen: dict[str, int] = {}
    ids = set()
    for item in items:
        section = str(item.get("section"))
        if seen.get(section, 0) < DESK_PER_SECTION:
            seen[section] = seen.get(section, 0) + 1
            ids.add(item["id"])
    return ids


def main(client=None):
    parser = argparse.ArgumentParser(description="Translate the Editor's Desk items into the per-item store.")
    parser.add_argument("--locale", default="ko", choices=locales.others(locales.DEFAULT))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    path = store_path(ROOT, args.locale)
    now = datetime.now(timezone.utc)
    model = translator.model_for("feed")
    ledger = translator.Ledger(ROOT / "data" / "i18n" / "translation_spend.json", now=lambda: now)
    print(f"localized_updates_budget usd_spent={ledger.spent:.4f} cap={ledger.monthly_cap:.2f} month={now:%Y-%m}")

    catalog = _fetch_catalog()
    if not catalog:
        print("No items in the editorial catalog!")
        return
    stored = load_store(path)
    sources = EnglishSources(ROOT)
    window = desk_window(catalog)

    # Resolve every item from artifacts and the last run's entry; what is left is the translation queue.
    resolved: dict[str, tuple[Texts, dict[str, str]]] = {}
    queue: list[tuple[dict[str, Any], list[str]]] = []
    reused = {"artifact": 0, "stored": 0}
    for item in catalog:
        texts: Texts = {}
        origin: dict[str, str] = {}
        old = stored.get(item["id"])
        old_fresh = isinstance(old, dict) and old.get("source_hash") == source_hash(item)
        from_artifact = artifact_texts(item, args.locale, ROOT, sources)
        for field in wanted_fields(item):
            if field in from_artifact:
                texts[field], origin[field] = from_artifact[field], "artifact"
                reused["artifact"] += 1
            elif old_fresh and clean(old.get(field)):
                texts[field], origin[field] = clean(old[field]), str((old.get("origin") or {}).get(field) or model)
                reused["stored"] += 1
        resolved[item["id"]] = (texts, origin)
        missing = [f for f in wanted_fields(item) if f not in texts]
        if missing and item["id"] in window:
            queue.append((item, missing))
    to_translate = queue[:MAX_TRANSLATIONS]

    if args.dry_run:
        print(f"\nDRY RUN: {len(catalog)} desk items.")
        print(f"  Texts reused: {reused['artifact']} from Korean artifacts, {reused['stored']} from the store")
        print(f"  Would translate: {len(to_translate)} of {len(queue)} items (max {MAX_TRANSLATIONS} per run)")
        return

    translated = 0
    if to_translate:
        print(f"Translating {len(to_translate)} items (max {MAX_TRANSLATIONS})...")
        try:
            client = client or translator.make_client()
        except Exception as exc:
            print(f" Cannot create the Anthropic client: {exc}", file=sys.stderr)
            to_translate = []
        for item, fields in to_translate:
            try:
                (result,) = translator.translate(
                    [item_job(item, fields)], args.locale, "feed", client=client, ledger=ledger
                )
            except translator.BudgetExceeded as exc:
                print(f"localized_updates_budget_cap_reached: {exc}", file=sys.stderr)
                break
            except translator.TranslationError as exc:
                print(f" Translation FAILED: {exc}", file=sys.stderr)
                continue
            except Exception as exc:
                print(f" Translation FAILED, stopping: {exc}", file=sys.stderr)
                break
            texts, origin = resolved[item["id"]]
            for field in fields:
                texts[field], origin[field] = clean(result.fields.get(field)), model
            translated += 1
        print(f" Translated {translated} items.")
    else:
        print("No desk item needs a translation.")

    items: dict[str, Entry] = {}
    for item in catalog:
        texts, origin = resolved[item["id"]]
        if not all(texts.get(f) for f in wanted_fields(item)):
            continue
        old = stored.get(item["id"])
        unchanged = (
            isinstance(old, dict) and old.get("source_hash") == source_hash(item)
            and all(old.get(f) == texts.get(f, "") for f in FIELDS)
        )
        items[item["id"]] = old if unchanged else {
            "source_hash": source_hash(item),
            "translated_at": now.isoformat(),
            "title": texts["title"],
            "summary": texts.get("summary", ""),
            "origin": origin,
        }
    links = localized_links(catalog, args.locale, ROOT)
    if items == stored and links == load_links(path):
        print(f"{len(items)} desk items unchanged in {path.relative_to(ROOT)}")
        return
    save_store(path, args.locale, items, links, now)
    print(f"Wrote {len(items)} of {len(catalog)} desk items to {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
