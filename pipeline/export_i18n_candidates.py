"""Export pre-translation candidates for an external translation system.

This command keeps translation selection cheap: list missing or stale pages
first, then ask an agent or external model to load only the selected source
payloads with ``--include-source``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_static_pages as render  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
I18N_DIR = ROOT / "data" / "i18n"

SURFACE_ORDER = {
    "daily": 10,
    "weekly": 20,
    "storyline": 30,
    "foundations": 40,
    "topic": 50,
    "story": 60,
}

SURFACE_CONTRACTS = {
    "daily": {
        "artifact_path": "data/i18n/<locale>/daily/<YYYY-MM-DD>.json",
        "translated_fields": [
            "title",
            "description",
            "intro",
            "highlights",
            "categories[].name",
            "categories[].summary",
            "categories[].articles[].title",
            "categories[].articles[].summary",
        ],
        "preserve_fields": ["url", "source", "published", "slug", "story links"],
    },
    "weekly": {
        "artifact_path": "data/i18n/<locale>/weekly/<YYYY-Www>.json",
        "translated_fields": [
            "title",
            "description",
            "intro",
            "highlights",
            "categories[].name",
            "categories[].summary",
            "categories[].articles[].title",
            "categories[].articles[].summary",
        ],
        "preserve_fields": ["url", "source", "published", "slug", "story links"],
    },
    "story": {
        "artifact_path": "data/i18n/<locale>/story/<sid>.json",
        "translated_fields": ["title", "description", "summary", "why_it_matters"],
        "preserve_fields": ["url", "source", "published", "sid"],
    },
    "storyline": {
        "artifact_path": "data/i18n/<locale>/storyline/<slug>.json",
        "translated_fields": ["title", "description", "editorial", "days[].items[].editor_note"],
        "preserve_fields": ["slug", "member sids", "source urls", "published dates"],
    },
    "topic": {
        "artifact_path": "data/i18n/<locale>/topic/<slug>.json",
        "translated_fields": ["title", "description", "summary", "sections[].html"],
        "preserve_fields": ["slug", "evidence", "related_storylines", "graph links"],
    },
    "foundations": {
        "artifact_path": "data/i18n/<locale>/foundations/<slug>.json",
        "translated_fields": ["title", "description", "summary", "sections[].html"],
        "preserve_fields": ["slug", "evidence", "links", "updated"],
    },
}

EXCLUDED_SURFACES = [
    {
        "surface": "feed",
        "path": "/",
        "reason": (
            "The feed is a live client-rendered surface backed by /api/feed and "
            "hourly ranking data, not a stable static page artifact. It needs a "
            "separate localized feed-data/API contract before export."
        ),
    }
]


def source_hash(source: dict[str, Any]) -> str:
    payload = json.dumps(source, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def artifact_path(locale: str, surface: str, ident: str) -> Path:
    return I18N_DIR / locale / surface / f"{ident}.json"


def load_artifact(locale: str, surface: str, ident: str) -> dict[str, Any] | None:
    data = render.load_json(artifact_path(locale, surface, ident))
    return data if isinstance(data, dict) else None


def source_title(surface: str, source: dict[str, Any]) -> str:
    if surface == "storyline":
        editorial = source.get("editorial") if isinstance(source.get("editorial"), dict) else {}
        return render.squeeze(editorial.get("title") or source.get("label") or source.get("slug"))
    return render.squeeze(
        source.get("title")
        or source.get("label")
        or source.get("name")
        or source.get("slug")
        or source.get("sid")
    )


def recap_description(recap: dict[str, Any]) -> str:
    intro = recap.get("intro") or []
    if isinstance(intro, str):
        intro = [intro]
    first_intro = next((render.squeeze(item) for item in intro if render.squeeze(item)), "")
    if first_intro:
        return render.clip(first_intro, 220)
    highlights = recap.get("highlights") or []
    first_highlight = next((render.squeeze(item) for item in highlights if render.squeeze(item)), "")
    if first_highlight:
        return render.clip(first_highlight, 220)
    return render.squeeze(recap.get("title"))


def source_description(surface: str, source: dict[str, Any]) -> str:
    if surface in {"daily", "weekly"}:
        return recap_description(source)
    if surface == "storyline":
        editorial = source.get("editorial") if isinstance(source.get("editorial"), dict) else {}
        return render.squeeze(editorial.get("tldr") or source.get("summary"))
    return render.squeeze(
        source.get("description")
        or source.get("summary")
        or source.get("summary_1line")
        or source.get("tldr")
    )


def candidate(
    *,
    locale: str,
    surface: str,
    ident: str,
    source_path: str,
    source: dict[str, Any],
    include_source: bool,
) -> dict[str, Any]:
    current_hash = source_hash(source)
    artifact = load_artifact(locale, surface, ident)
    existing_hash = str((artifact or {}).get("source_hash") or "")
    if not artifact:
        status = "missing"
    elif existing_hash != current_hash:
        status = "stale"
    else:
        status = "fresh"

    item: dict[str, Any] = {
        "locale": locale,
        "surface": surface,
        "id": ident,
        "source_path": source_path,
        "target_path": f"/{locale}{source_path}",
        "artifact_path": str(artifact_path(locale, surface, ident).relative_to(ROOT)),
        "status": status,
        "source_hash": current_hash,
        "existing_source_hash": existing_hash or None,
        "title": source_title(surface, source),
        "description": source_description(surface, source),
        "contract": SURFACE_CONTRACTS[surface],
    }
    if include_source:
        item["source"] = source
    return item


def iter_sources() -> list[tuple[str, str, str, dict[str, Any]]]:
    stories = render.load_store()
    storylines = {
        str(item.get("slug")): item
        for item in render.load_storyline_details()
        if isinstance(item, dict) and item.get("slug")
    }
    wiki = render.load_wiki()
    foundations = render.load_foundations()

    rows: list[tuple[str, str, str, dict[str, Any]]] = []
    for recap in render.load_recaps(render.DAILY_DIR, render.DATE_FILE_RE, "date"):
        ident = str(recap.get("date"))
        rows.append(("daily", ident, f"/daily/{ident}", recap))
    for recap in render.load_recaps(render.WEEKLY_DIR, render.WEEK_FILE_RE, "week"):
        ident = str(recap.get("week"))
        rows.append(("weekly", ident, f"/weekly/{ident}", recap))
    for slug, source in sorted(storylines.items()):
        rows.append(("storyline", slug, f"/storyline/{slug}", source))
    for slug, source in sorted((foundations.get("concepts") or {}).items()):
        if isinstance(source, dict):
            rows.append(("foundations", str(slug), f"/foundations/{slug}", source))
    for slug, source in sorted((wiki.get("nodes") or {}).items()):
        if isinstance(source, dict):
            rows.append(("topic", str(slug), f"/topic/{slug}", source))
    for sid, source in sorted(stories.items()):
        if isinstance(source, dict):
            rows.append(("story", str(sid), f"/story/{sid}", source))
    return rows


def build_export(
    *,
    locale: str,
    surfaces: set[str] | None = None,
    include_fresh: bool = False,
    include_source: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    items = []
    for surface, ident, source_path, source in iter_sources():
        if surfaces and surface not in surfaces:
            continue
        item = candidate(
            locale=locale,
            surface=surface,
            ident=ident,
            source_path=source_path,
            source=source,
            include_source=include_source,
        )
        if include_fresh or item["status"] != "fresh":
            items.append(item)

    items.sort(
        key=lambda item: (
            SURFACE_ORDER.get(str(item["surface"]), 99),
            0 if item["status"] == "stale" else 1,
            str(item["source_path"]),
        )
    )
    if limit is not None:
        items = items[: max(0, limit)]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "locale": locale,
        "include_fresh": include_fresh,
        "include_source": include_source,
        "surfaces": sorted(surfaces) if surfaces else sorted(SURFACE_ORDER, key=SURFACE_ORDER.get),
        "excluded_surfaces": EXCLUDED_SURFACES,
        "item_count": len(items),
        "items": items,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locale", default="ko", help="Target locale, e.g. ko")
    parser.add_argument(
        "--surface",
        action="append",
        choices=sorted(SURFACE_ORDER),
        help="Limit to a surface; repeat for multiple surfaces",
    )
    parser.add_argument("--include-fresh", action="store_true", help="Include already fresh artifacts")
    parser.add_argument("--include-source", action="store_true", help="Embed English source objects")
    parser.add_argument("--limit", type=int, default=100, help="Maximum items to output")
    parser.add_argument("--output", type=Path, help="Write JSON to this path instead of stdout")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_export(
        locale=args.locale,
        surfaces=set(args.surface or []) or None,
        include_fresh=args.include_fresh,
        include_source=args.include_source,
        limit=args.limit,
    )
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
