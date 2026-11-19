"""Agent-written translations of daily and weekly recaps.

The recap routines write the Korean version of each recap in the same run as
the English one, using this helper so the artifact matches what the localized
static pages and the Korean email already read
(``data/i18n/<locale>/<kind>/<id>.json``):

    # 1. Export the fields to translate (English text, in recap order)
    python pipeline/recap_i18n.py skeleton --kind daily --id 2026-11-18 --output /tmp/ko.json
    # 2. Replace every English string in that file with its translation
    # 3. Validate and write the artifact (adds locale, source hash, metadata)
    python pipeline/recap_i18n.py write --kind daily --id 2026-11-18 --input /tmp/ko.json --model "<model>"
    # Check an existing artifact is present and fresh
    python pipeline/recap_i18n.py check --kind daily --id 2026-11-18

The English recap is the source of truth: the artifact keeps its category and
article order and every article URL, and translates only reader-facing text.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import render_static_pages as render  # noqa: E402

ROOT = render.ROOT
I18N_DIR = ROOT / "data" / "i18n"
KINDS = {
    "daily": {"dir": render.DAILY_DIR, "id_re": re.compile(r"^\d{4}-\d{2}-\d{2}$")},
    "weekly": {"dir": render.WEEKLY_DIR, "id_re": re.compile(r"^\d{4}-W\d{2}$")},
}
SCRIPT_CHECKS = {"ko": re.compile(r"[가-힣]")}
MAX_FIELD_CHARS = 1200
# Readability caps per locale: a title fits the hero in about three lines on
# a phone, a highlight in about three lines of the "30 seconds" list.
MAX_TITLE_CHARS = {"ko": 40}
MAX_HIGHLIGHT_CHARS = {"ko": 100}
MAX_CATEGORY_NAME_CHARS = {"ko": 40}


def _intro_list(value) -> list[str]:
    if isinstance(value, str):
        return [p.strip() for p in re.split(r"\n\s*\n", value) if p.strip()]
    if isinstance(value, list):
        return [str(p).strip() for p in value if isinstance(p, str) and p.strip()]
    return []


def load_source(kind: str, ident: str) -> dict:
    spec = KINDS[kind]
    if not spec["id_re"].match(ident):
        raise SystemExit(f"bad {kind} id: {ident}")
    path = spec["dir"] / f"{ident}.json"
    if not path.exists():
        raise SystemExit(f"no English {kind} recap at {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def artifact_path(kind: str, ident: str, locale: str) -> Path:
    return I18N_DIR / locale / kind / f"{ident}.json"


def skeleton(source: dict) -> dict:
    """The translatable fields of a recap, still in English."""
    return {
        "title": source.get("title") or "",
        "description": render.recap_description(source),
        "intro": _intro_list(source.get("intro")),
        "highlights": [h for h in source.get("highlights") or [] if isinstance(h, str)],
        "categories": [
            {
                "name": c.get("name") or "",
                "summary": c.get("summary") or "",
                "articles": [
                    {"url": a.get("url") or "", "title": a.get("title") or "", "summary": a.get("summary") or ""}
                    for a in c.get("articles") or []
                    if isinstance(a, dict)
                ],
            }
            for c in source.get("categories") or []
            if isinstance(c, dict)
        ],
    }


def validate(translated: dict, source: dict, locale: str) -> list[str]:
    """Problems that block writing the artifact; empty means OK."""
    errs: list[str] = []
    if not isinstance(translated, dict):
        return ["translation is not an object"]
    want = skeleton(source)
    script = SCRIPT_CHECKS.get(locale)

    def text(value, where, *, needs_script=True):
        if not isinstance(value, str) or not value.strip():
            errs.append(f"{where}: empty")
            return
        if len(value) > MAX_FIELD_CHARS:
            errs.append(f"{where}: over {MAX_FIELD_CHARS} chars")
        if needs_script and script and not script.search(value):
            errs.append(f"{where}: not translated (no {locale} text)")

    text(translated.get("title"), "title")
    cap = MAX_TITLE_CHARS.get(locale)
    if cap and isinstance(translated.get("title"), str) and len(translated["title"].strip()) > cap:
        errs.append(f"title: over {cap} chars ({len(translated['title'].strip())})")
    if translated.get("description") is not None:
        text(translated.get("description"), "description")
    intro = translated.get("intro")
    if not isinstance(intro, list) or len(intro) != len(want["intro"]):
        errs.append(f"intro: expected {len(want['intro'])} paragraphs")
    else:
        for i, p in enumerate(intro):
            text(p, f"intro[{i}]")
    highlights = translated.get("highlights") or []
    if len(highlights) != len(want["highlights"]):
        errs.append(f"highlights: expected {len(want['highlights'])} items")
    else:
        for i, h in enumerate(highlights):
            text(h, f"highlights[{i}]")
            cap = MAX_HIGHLIGHT_CHARS.get(locale)
            if cap and isinstance(h, str) and len(h.strip()) > cap:
                errs.append(f"highlights[{i}]: over {cap} chars ({len(h.strip())})")
    cats = translated.get("categories")
    if not isinstance(cats, list) or len(cats) != len(want["categories"]):
        return errs + [f"categories: expected {len(want['categories'])} in English order"]
    for ci, (cat, src) in enumerate(zip(cats, want["categories"])):
        where = f"categories[{ci}]"
        if not isinstance(cat, dict):
            errs.append(f"{where}: not an object")
            continue
        text(cat.get("name"), f"{where}.name")
        cap = MAX_CATEGORY_NAME_CHARS.get(locale)
        if cap and isinstance(cat.get("name"), str) and len(cat["name"].strip()) > cap:
            errs.append(f"{where}.name: over {cap} chars")
        text(cat.get("summary"), f"{where}.summary")
        arts = cat.get("articles")
        if not isinstance(arts, list) or len(arts) != len(src["articles"]):
            errs.append(f"{where}.articles: expected {len(src['articles'])} in English order")
            continue
        for ai, (art, src_art) in enumerate(zip(arts, src["articles"])):
            aw = f"{where}.articles[{ai}]"
            if not isinstance(art, dict):
                errs.append(f"{aw}: not an object")
                continue
            if art.get("url") != src_art["url"]:
                errs.append(f"{aw}.url: must stay {src_art['url']}")
            # Titles can stay in English when they are a product or paper name.
            text(art.get("title"), f"{aw}.title", needs_script=False)
            text(art.get("summary"), f"{aw}.summary")
    return errs


def build_artifact(kind: str, ident: str, locale: str, translated: dict, source: dict, model: str) -> dict:
    artifact = {
        "locale": locale,
        "source_path": f"/{kind}/{ident}",
        "source_hash": render.i18n_source_hash(source),
        "translated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "model": model,
        "review_status": "machine",
        "title": translated["title"].strip(),
        "intro": [p.strip() for p in translated["intro"]],
        "highlights": [h.strip() for h in translated.get("highlights") or []],
        "categories": [
            {
                "name": c["name"].strip(),
                "summary": c["summary"].strip(),
                "articles": [
                    {"url": a["url"], "title": a["title"].strip(), "summary": a["summary"].strip()}
                    for a in c["articles"]
                ],
            }
            for c in translated["categories"]
        ],
    }
    if translated.get("description"):
        artifact["description"] = translated["description"].strip()
    return artifact


def check(kind: str, ident: str, locale: str) -> list[str]:
    path = artifact_path(kind, ident, locale)
    if not path.exists():
        return [f"missing {path.relative_to(ROOT)}"]
    artifact = json.loads(path.read_text(encoding="utf-8"))
    source = load_source(kind, ident)
    errs = []
    if not render.i18n_hash_matches(artifact.get("source_hash"), source):
        errs.append("stale: the English recap changed after this translation")
    errs += validate(artifact, source, locale)
    return errs


def load_localized(kind: str, ident: str, locale: str) -> dict | None:
    """The source recap with a fresh translation overlaid, or None."""
    if kind not in KINDS or not KINDS[kind]["id_re"].match(str(ident or "")):
        return None
    path = artifact_path(kind, ident, locale)
    src_path = KINDS[kind]["dir"] / f"{ident}.json"
    if not path.exists() or not src_path.exists():
        return None
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
        source = json.loads(src_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    if not render.i18n_hash_matches(artifact.get("source_hash"), source):
        return None
    return render.localized_recap_overlay(source, artifact)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("skeleton", "write", "check"):
        p = sub.add_parser(name)
        p.add_argument("--kind", choices=sorted(KINDS), required=True)
        p.add_argument("--id", required=True)
        p.add_argument("--locale", default="ko")
        if name == "skeleton":
            p.add_argument("--output")
        if name == "write":
            p.add_argument("--input", required=True)
            p.add_argument("--model", required=True, help="the model that translated it")
    args = ap.parse_args(argv)
    source = load_source(args.kind, args.id)
    if args.cmd == "skeleton":
        text = json.dumps(skeleton(source), ensure_ascii=False, indent=2) + "\n"
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
            print(f"RECAP_I18N_SKELETON path={args.output}")
        else:
            print(text)
        return 0
    if args.cmd == "write":
        translated = json.loads(Path(args.input).read_text(encoding="utf-8"))
        errs = validate(translated, source, args.locale)
        if errs:
            print(f"RECAP_I18N_INVALID kind={args.kind} id={args.id} locale={args.locale}")
            for e in errs:
                print(f"  - {e}")
            return 1
        path = artifact_path(args.kind, args.id, args.locale)
        path.parent.mkdir(parents=True, exist_ok=True)
        artifact = build_artifact(args.kind, args.id, args.locale, translated, source, args.model)
        path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"RECAP_I18N_OK kind={args.kind} id={args.id} locale={args.locale} path={path.relative_to(ROOT)}")
        return 0
    errs = check(args.kind, args.id, args.locale)
    if errs:
        print(f"RECAP_I18N_INVALID kind={args.kind} id={args.id} locale={args.locale}")
        for e in errs:
            print(f"  - {e}")
        return 1
    print(f"RECAP_I18N_OK kind={args.kind} id={args.id} locale={args.locale}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
