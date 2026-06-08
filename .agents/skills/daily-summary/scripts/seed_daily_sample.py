"""Generate a deterministic *sample* daily recap from an input bundle.

This is NOT the real summarizer — it produces placeholder narrative text using
the article metadata we already have, so the /daily UI can be reviewed before
an agent (Claude Code routine) is wired up. It also serves as a concrete
reference for the recap schema the agent must emit.

Usage:
    python seed_daily_sample.py                 # uses input/latest.json
    python seed_daily_sample.py --date 2026-06-07
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone

from daily_common import (
    DAILY_DIR,
    DAILY_INPUT_DIR,
    fmt_day,
    load_json,
    slugify,
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
        f"{count} item{'s' if count != 1 else ''} today under {name}. "
        + (f"Headlined by “{lead}”. " if lead else "")
        + "(Placeholder summary — the agent replaces this with a real recap.)"
    )


def build_sample(bundle: dict) -> dict:
    day = bundle["date"]
    d = date.fromisoformat(day)
    range_label = bundle.get("range_label") or fmt_day(d)

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
    # `intro` is an array of paragraph strings and `highlights` a scannable
    # bullet list — the same shape a real recap emits, so the sample exercises
    # the live /daily layout.
    intro = [
        f"Today ({range_label}) the feed surfaced {total} unique articles across "
        f"{len(categories)} categories. The biggest threads ran through "
        + ", ".join(c["name"] for c in categories)
        + ".",
        "This is placeholder narrative text — a Claude Code routine will replace it "
        "with a real “what happened in AI today” overview drawn from the article summaries below.",
    ]
    highlights = [
        f"{c['name']}: {c['articles'][0]['title']}"
        for c in categories[:5]
        if c.get("articles")
    ] or ["Placeholder highlight — the agent replaces these with real one-line takeaways."]

    return {
        "date": day,
        "title": f"What happened in AI — {range_label}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "seed_daily_sample (placeholder)",
        "intro": intro,
        "highlights": highlights,
        "article_count": total,
        "categories": categories,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", help="date id; defaults to input/latest.json")
    args = ap.parse_args()

    input_path = DAILY_INPUT_DIR / (f"{args.date}.json" if args.date else "latest.json")
    bundle = load_json(input_path, None)
    if bundle is None:
        raise SystemExit(f"input bundle not found: {input_path}. Run build_daily_input.py first.")

    recap = build_sample(bundle)
    out = DAILY_DIR / f"{recap['date']}.json"
    write_json(out, recap)
    print(f"wrote sample recap: data/daily/{out.name} ({recap['article_count']} articles, {len(recap['categories'])} categories)")


if __name__ == "__main__":
    main()
