"""Replay the deck selector against published recaps.

For each daily date or weekly id it rebuilds the judged candidate pool for
the recap's window (``pipeline/deck_candidates.py``), runs the selector
(``pipeline/deck_select.py``) at the published recap's size, and reports:

- the recall funnel: Jev keeps -> any feed edition -> recap bundle ->
  published recap, and Jev keeps -> selector shortlist;
- overlap between the published recap and the shortlist;
- silver must-cover recall (multi-source stories and storyline members) for
  both lists - biased toward the selector, which scores coverage, and small on
  single-day windows, so use it as a smoke test only. Feed position is not a
  silver signal: on quiet days the feed's top slots are community posts, so it
  measures agreement with feed ranking, not importance;
- with owner labels: must-cover recall@K, alpha-nDCG@K and graded sum for
  both lists.

``--packet`` writes a labeling file per window under
``data/quality/deck_benchmark/labels/`` with every story either list picked.
Stories both lists picked are prefilled with grade 1; disagreements are left
null. Existing label files are never overwritten (new stories are appended).

Usage:
    python scripts/deck_replay.py --deck daily --from 2026-10-24 --to 2026-10-27 --packet
    python scripts/deck_replay.py --deck weekly --week 2026-W44
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import deck_candidates as dc  # noqa: E402
import deck_metrics as dm  # noqa: E402
import deck_select as ds  # noqa: E402

BENCH_DIR = ROOT / "data" / "quality" / "deck_benchmark"
LABELS_DIR = BENCH_DIR / "labels"
RUNS_DIR = BENCH_DIR / "runs"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")
WEEK_RE = re.compile(r"^\d{4}-W\d{2}\.json$")

GUIDE = (
    "grade: 2 = must-read (the recap is wrong without it), 1 = useful, 0 = should not be in the recap. "
    "same_as: story_id of another story in this file about the same event. note: optional."
)


def _read(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def recap_urls(recap: dict[str, Any]) -> list[str]:
    out = []
    for category in recap.get("categories") or []:
        for article in category.get("articles") or []:
            url = dc.normalize_url(article.get("url"))
            if url and url not in out:
                out.append(url)
    return out


def recap_articles(recap: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out = {}
    for category in recap.get("categories") or []:
        for article in category.get("articles") or []:
            out.setdefault(dc.normalize_url(article.get("url")), article)
    return out


# --- windows --------------------------------------------------------------


def daily_windows(start: date, end: date) -> list[dict[str, Any]]:
    windows = []
    day = start
    while day <= end:
        label = day.isoformat()
        prior = set()
        for path in (ROOT / "data" / "daily").glob("*.json"):
            if DATE_RE.match(path.name) and path.stem < label:
                prior.update(recap_urls(_read(path, {})))
        windows.append(
            {
                "label": label,
                "start": day,
                "end": day,
                "recap": _read(ROOT / "data" / "daily" / f"{label}.json", None),
                "bundle": _read(ROOT / "data" / "daily" / "input" / f"{label}.json", None),
                "prior_urls": prior,
            }
        )
        day += timedelta(days=1)
    return windows


def weekly_window(week: str) -> dict[str, Any]:
    recap = _read(ROOT / "data" / "weekly" / f"{week}.json", None)
    bundle = _read(ROOT / "data" / "weekly" / "input" / f"{week}.json", None)
    source = recap or bundle
    if source and source.get("start") and source.get("end"):
        start, end = date.fromisoformat(source["start"]), date.fromisoformat(source["end"])
    else:
        # Production runs Friday over the trailing seven days (Sat-Fri).
        year, number = week.split("-W")
        monday = date.fromisocalendar(int(year), int(number), 1)
        start, end = monday - timedelta(days=2), monday + timedelta(days=4)
    prior = set()
    for path in (ROOT / "data" / "weekly").glob("*.json"):
        if WEEK_RE.match(path.name) and path.stem < week:
            prior.update(recap_urls(_read(path, {})))
    return {"label": week, "start": start, "end": end, "recap": recap, "bundle": bundle, "prior_urls": prior}


# --- silver set -----------------------------------------------------------


def storyline_urls() -> set[str]:
    index = _read(ROOT / "data" / "storylines" / "index.json", {})
    urls = set()
    for line in (index or {}).get("storylines") or []:
        urls.update(dc.normalize_url(u) for u in line.get("member_urls") or [])
    return urls


def silver_reasons(story: dict[str, Any], storyline: set[str]) -> list[str]:
    reasons = []
    if int(story.get("source_count") or 1) >= 2:
        reasons.append("multi_source")
    if any(dc.normalize_url(u) in storyline for u in story.get("member_urls") or []):
        reasons.append("storyline")
    return reasons


# --- replay ---------------------------------------------------------------


def replay_window(deck: str, window: dict[str, Any], cfg: dict[str, Any], storyline: set[str]) -> dict[str, Any]:
    spec = ds.deck_config(deck, cfg)
    types = set(spec.get("types") or []) or None
    rows = dc.load_rows(window["start"], window["end"])
    all_types, _ = dc.filter_rows(rows, window["start"], window["end"], types=None, exclude_urls=window["prior_urls"], include_dropped=True)
    candidates, rejects = dc.filter_rows(rows, window["start"], window["end"], types=types, exclude_urls=window["prior_urls"])
    stories = ds.score_stories(candidates, cfg)
    by_url = {}
    for story in stories:
        for url in story.get("member_urls") or []:
            by_url[dc.normalize_url(url)] = story["story_id"]

    recap = window.get("recap") or {}
    published_urls = recap_urls(recap)
    published_articles = recap_articles(recap)
    bundle_urls = {dc.normalize_url(a.get("url")) for a in (window.get("bundle") or {}).get("articles") or []}
    budget = len(published_urls) or int(spec.get("budget", 0))
    selection = ds.select(candidates, deck, cfg=cfg, budget=budget)

    story_index = {s["story_id"]: s for s in stories}
    outside = {}
    published_ids: list[str] = []
    for url in published_urls:
        sid = by_url.get(url)
        if sid is None:
            sid = f"url:{url}"
            article = published_articles.get(url, {})
            outside[sid] = {"story_id": sid, "url": url, "title": article.get("title"), "source": article.get("source"), "outside_pool": True}
        if sid not in published_ids:
            published_ids.append(sid)
    selected_ids = [card["story_id"] for card in selection["shortlist"]]

    # Funnel over URLs in the deck's types (release items are not "keeps").
    keep_urls = {r["key"] for r in all_types if r.get("judge_verdict") == "keep" and (types is None or str(r.get("type") or "news") in types)}
    edition_urls = {r["key"] for r in all_types if int(r.get("edition_runs") or 0) > 0}
    selected_urls = {dc.normalize_url(u) for card in selection["shortlist"] for u in card.get("member_urls") or []}
    funnel = {
        "jev_keep": len(keep_urls),
        "keep_in_edition": len(keep_urls & edition_urls),
        "keep_in_bundle": len(keep_urls & bundle_urls),
        "keep_in_published": len(keep_urls & set(published_urls)),
        "keep_in_shortlist": len(keep_urls & selected_urls),
        "bundle": len(bundle_urls),
        "published": len(published_urls),
        "published_outside_pool": len(outside),
    }

    silver = {sid for sid, s in story_index.items() if silver_reasons(s, storyline)}
    both = [sid for sid in published_ids if sid in set(selected_ids)]
    return {
        "label": window["label"],
        "window": [window["start"].isoformat(), window["end"].isoformat()],
        "has_recap": bool(published_urls),
        "budget": budget,
        "candidates": len(candidates),
        "stories": len(stories),
        "rejects": rejects,
        "funnel": funnel,
        "published_ids": published_ids,
        "selected_ids": selected_ids,
        "overlap": len(both),
        "silver_count": len(silver),
        "silver_recall": {
            "published": dm.must_cover_recall(published_ids, silver),
            "selector": dm.must_cover_recall(selected_ids, silver),
        },
        "published_sources": Counter(str((story_index.get(s) or outside.get(s) or {}).get("source")) for s in published_ids).most_common(3),
        "selector_sources": Counter(card.get("source") for card in selection["shortlist"]).most_common(3),
        "selection": selection,
        "_stories": {**{sid: story_index[sid] for sid in set(published_ids + selected_ids) if sid in story_index}, **outside},
        "_silver": silver,
    }


# --- labels ---------------------------------------------------------------


def label_path(deck: str, label: str) -> Path:
    return LABELS_DIR / f"{deck}-{label}.json"


def write_packet(deck: str, result: dict[str, Any], storyline: set[str]) -> tuple[Path, int, int]:
    path = label_path(deck, result["label"])
    existing = _read(path, None) or {
        "deck": deck,
        "window": result["label"],
        "guide": GUIDE,
        "stories": {},
    }
    stories = existing.setdefault("stories", {})
    published = set(result["published_ids"])
    selected = set(result["selected_ids"])
    added = 0
    for sid in result["published_ids"] + [s for s in result["selected_ids"] if s not in published]:
        if sid in stories:
            continue
        story = result["_stories"].get(sid, {})
        picked_by = "both" if sid in published and sid in selected else ("published" if sid in published else "selector")
        stories[sid] = {
            "grade": 1 if picked_by == "both" else None,
            "same_as": None,
            "note": "",
            "picked_by": picked_by,
            "title": story.get("title"),
            "url": story.get("url") or story.get("key"),
            "source": story.get("source"),
            "judge_score": story.get("judge_score"),
            "judge_category": story.get("judge_category"),
            "summary": (story.get("summary") or "")[:280],
            "silver": silver_reasons(story, storyline) if story else [],
        }
        added += 1
    _write(path, existing)
    open_items = sum(1 for s in stories.values() if s.get("grade") is None)
    return path, added, open_items


def labeled_metrics(deck: str, result: dict[str, Any]) -> dict[str, Any] | None:
    labels = _read(label_path(deck, result["label"]), None)
    if not labels:
        return None
    entries = labels.get("stories") or {}
    grades = {sid: float(e["grade"]) for sid, e in entries.items() if e.get("grade") is not None}
    pending = sum(1 for e in entries.values() if e.get("grade") is None)
    if not grades:
        return {"labeled": 0, "pending": pending}
    groups = dm.duplicate_groups({sid: e.get("same_as") for sid, e in entries.items()})
    must = {sid for sid, grade in grades.items() if grade >= 2}
    k = result["budget"]
    out = {"labeled": len(grades), "pending": pending, "must": len(must)}
    for name, ids in (("published", result["published_ids"]), ("selector", result["selected_ids"])):
        out[name] = {
            "must_cover_recall": dm.must_cover_recall(ids, must, k),
            "alpha_ndcg": dm.alpha_ndcg(ids, grades, groups, alpha=0.5, k=k),
            "graded_sum": dm.graded_sum(ids, grades),
            "drops": sum(1 for sid in ids if grades.get(sid) == 0),
        }
    return out


# --- report ---------------------------------------------------------------


def _pct(value: float | None) -> str:
    return "-" if value is None else f"{value:.0%}"


def render(deck: str, results: list[dict[str, Any]]) -> str:
    lines = [
        f"# Deck selector replay: {deck}",
        "",
        f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}. Selector run at each published recap's size.",
        "",
        "## Funnel (URLs in the deck's item types)",
        "",
        "| window | Jev keep | in edition | in bundle | in recap | in shortlist | recap cards | recap outside pool |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in results:
        f = r["funnel"]
        lines.append(
            f"| {r['label']} | {f['jev_keep']} | {f['keep_in_edition']} | {f['keep_in_bundle']} | {f['keep_in_published']} | {f['keep_in_shortlist']} | {f['published']} | {f['published_outside_pool']} |"
        )
    lines += [
        "",
        "## Published recap vs selector",
        "",
        "Silver must-cover = multi-source stories and storyline members. The selector scores coverage, so silver recall favors it, and single-day sets are small; treat it as a smoke test. Owner labels decide.",
        "",
        "| window | K | overlap | silver n | silver recall: recap | silver recall: selector | recap top sources | selector top sources |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for r in results:
        if not r["has_recap"]:
            lines.append(f"| {r['label']} | {r['budget']} | - | {r['silver_count']} | - | {_pct(r['silver_recall']['selector'])} | (no recap yet) | {r['selector_sources']} |")
            continue
        lines.append(
            f"| {r['label']} | {r['budget']} | {r['overlap']} | {r['silver_count']} | {_pct(r['silver_recall']['published'])} | {_pct(r['silver_recall']['selector'])} | {r['published_sources']} | {r['selector_sources']} |"
        )
    labeled = [r for r in results if r.get("labels") and r["labels"].get("labeled")]
    lines += ["", "## Labeled metrics", ""]
    if not labeled:
        lines.append("No graded labels yet. Run with `--packet`, grade the files in `data/quality/deck_benchmark/labels/`, then rerun.")
    else:
        lines += [
            "| window | labeled | pending | must | recall@K recap | recall@K selector | alpha-nDCG recap | alpha-nDCG selector | grade sum recap | grade sum selector | drops recap | drops selector |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for r in labeled:
            m = r["labels"]
            p, s = m["published"], m["selector"]
            lines.append(
                f"| {r['label']} | {m['labeled']} | {m['pending']} | {m['must']} | {_pct(p['must_cover_recall'])} | {_pct(s['must_cover_recall'])} | {p['alpha_ndcg']} | {s['alpha_ndcg']} | {p['graded_sum']} | {s['graded_sum']} | {p['drops']} | {s['drops']} |"
            )
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--deck", choices=["daily", "weekly"], required=True)
    ap.add_argument("--from", dest="start", help="daily: first date YYYY-MM-DD")
    ap.add_argument("--to", dest="end", help="daily: last date YYYY-MM-DD (default: --from)")
    ap.add_argument("--week", action="append", help="weekly: ISO week id, repeatable")
    ap.add_argument("--packet", action="store_true", help="write/extend label files for owner grading")
    ap.add_argument("--out", help="report directory (default data/quality/deck_benchmark/runs/<deck>-<stamp>)")
    args = ap.parse_args()

    if args.deck == "daily":
        if not args.start:
            ap.error("--from is required for the daily deck")
        windows = daily_windows(date.fromisoformat(args.start), date.fromisoformat(args.end or args.start))
    else:
        if not args.week:
            ap.error("--week is required for the weekly deck")
        windows = [weekly_window(week) for week in args.week]

    cfg = ds.load_config()
    storyline = storyline_urls()
    results = []
    for window in windows:
        result = replay_window(args.deck, window, cfg, storyline)
        if args.packet and (result["published_ids"] or result["selected_ids"]):
            path, added, pending = write_packet(args.deck, result, storyline)
            result["packet"] = {"path": str(path.relative_to(ROOT)), "added": added, "pending": pending}
        result["labels"] = labeled_metrics(args.deck, result)
        results.append(result)
        print(
            "deck_replay "
            f"deck={args.deck} window={result['label']} candidates={result['candidates']} stories={result['stories']} "
            f"K={result['budget']} overlap={result['overlap']} keep={result['funnel']['jev_keep']} "
            f"keep_in_bundle={result['funnel']['keep_in_bundle']} keep_in_shortlist={result['funnel']['keep_in_shortlist']} "
            f"packet={result.get('packet', {}).get('path', '-')} pending={result.get('packet', {}).get('pending', '-')}"
        )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out) if args.out else RUNS_DIR / f"{args.deck}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.md").write_text(render(args.deck, results), encoding="utf-8")
    public = [{k: v for k, v in r.items() if not k.startswith("_")} for r in results]
    _write(out_dir / "report.json", public)
    print(f"deck_replay_report path={out_dir / 'report.md'}")


if __name__ == "__main__":
    main()
