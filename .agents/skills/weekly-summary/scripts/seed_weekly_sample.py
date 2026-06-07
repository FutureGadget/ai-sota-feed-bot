"""Generate a deterministic *sample* weekly recap from an input bundle.

This is NOT the real summarizer — it produces placeholder narrative text using
the article metadata we already have, so the /weekly UI can be reviewed before
an agent (Claude Code routine) is wired up. It also serves as a concrete
reference for the recap schema the agent must emit.

Usage:
    python pipeline/seed_weekly_sample.py                 # uses input/latest.json
    python pipeline/seed_weekly_sample.py --week 2026-W23
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from weekly_common import (
    WEEKLY_DIR,
    WEEKLY_INPUT_DIR,
    fmt_range,
    load_json,
    slugify,
    week_bounds,
    write_json,
)

# Per-article cap so the sample page stays readable.
MAX_PER_CATEGORY = 8

# Rough keyword-based themes, in display order. The placeholder generator
# assigns each article to the FIRST theme whose keywords match its title/summary,
# so the sample page resembles the thematic split a real recap would have.
# The live agent decides the real themes; this is only an approximation.
THEMES: list[tuple[str, list[str]]] = [
    ("Models & Releases", [
        "release", "launch", "announc", "unveil", "model", "gpt", "claude",
        "gemini", "llama", "mistral", "qwen", "open-source", "open source",
        "weights", "fine-tun", "version", "preview", "ships",
    ]),
    ("Agents & Tooling", [
        "agent", "mcp", "copilot", "ide", " sdk", "framework", "orchestrat",
        "workflow", "tool", "plugin", "assistant", "coding", "automation",
    ]),
    ("Research & Techniques", [
        "paper", "benchmark", "research", "training", "reasoning", "reinforcement",
        "architecture", "scaling", "evaluation", "study", "technique", "method",
        "fine-tuning", "distill", "rag", "retrieval",
    ]),
    ("Infrastructure & Compute", [
        "gpu", "nvidia", "chip", "datacenter", "data center", "compute",
        "inference", "cluster", "hardware", "cloud", "tpu", "serving", "latency",
    ]),
    ("Funding & Business", [
        "funding", "raise", "raised", "valuation", "acqui", "ipo", "revenue",
        "startup", "billion", "million", "investment", "deal", "partnership",
        "hire", "layoff", "ceo",
    ]),
    ("Safety & Policy", [
        "safety", "regulat", "policy", "govern", "ai act", "lawsuit", "copyright",
        "privacy", "security", "risk", "alignment", "ban", "court", "ethic",
    ]),
]
FALLBACK_THEME = "More in AI"


def classify_theme(article: dict) -> str:
    text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
    for name, keywords in THEMES:
        if any(kw in text for kw in keywords):
            return name
    return FALLBACK_THEME


def category_blurb(name: str, count: int, top_titles: list[str]) -> str:
    lead = top_titles[0] if top_titles else ""
    return (
        f"{count} item{'s' if count != 1 else ''} this week under {name}. "
        + (f"Headlined by “{lead}”. " if lead else "")
        + "(Placeholder summary — the agent replaces this with a real recap.)"
    )


def build_sample(bundle: dict) -> dict:
    week = bundle["week"]
    start_d, end_d = week_bounds(week)
    range_label = bundle.get("range_label") or fmt_range(start_d, end_d)

    grouped: dict[str, list] = {}
    for a in bundle.get("articles", []):
        grouped.setdefault(classify_theme(a), []).append(a)

    # Display order: defined themes first, then the fallback bucket last.
    theme_order = [name for name, _ in THEMES] + [FALLBACK_THEME]

    categories = []
    for name in theme_order:
        arts = grouped.get(name) or []
        if not arts:
            continue
        top_titles = [a["title"] for a in arts[:MAX_PER_CATEGORY]]
        categories.append(
            {
                "name": name,
                "slug": slugify(name),
                "summary": category_blurb(name, len(arts), top_titles),
                "articles": [
                    {
                        "title": a["title"],
                        "summary": a.get("summary") or "",
                        "source": a.get("source"),
                        "url": a.get("url"),
                        "published": a.get("published"),
                    }
                    for a in arts[:MAX_PER_CATEGORY]
                ],
            }
        )

    total = bundle.get("article_count", len(bundle.get("articles", [])))
    intro = (
        f"This week ({range_label}) the feed surfaced {total} unique articles across "
        f"{len(categories)} categories. The biggest threads ran through "
        + ", ".join(c["name"] for c in categories)
        + ". This is placeholder narrative text — a Claude Code routine will replace it "
        "with a real “what happened in AI this week” overview drawn from the article summaries below."
    )

    return {
        "week": week,
        "start": start_d.isoformat(),
        "end": end_d.isoformat(),
        "title": f"What happened in AI — {range_label}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "seed_weekly_sample (placeholder)",
        "intro": intro,
        "article_count": total,
        "categories": categories,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--week", help="ISO week id; defaults to input/latest.json")
    args = ap.parse_args()

    input_path = WEEKLY_INPUT_DIR / (f"{args.week}.json" if args.week else "latest.json")
    bundle = load_json(input_path, None)
    if bundle is None:
        raise SystemExit(f"input bundle not found: {input_path}. Run build_weekly_input.py first.")

    recap = build_sample(bundle)
    out = WEEKLY_DIR / f"{recap['week']}.json"
    write_json(out, recap)
    print(f"wrote sample recap: data/weekly/{out.name} ({recap['article_count']} articles, {len(recap['categories'])} categories)")


if __name__ == "__main__":
    main()
