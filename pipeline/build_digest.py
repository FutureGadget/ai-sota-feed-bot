from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dateutil import parser as dt_parser

ROOT = Path(__file__).resolve().parents[1]


def load_profile() -> dict[str, Any]:
    with open(ROOT / "config" / "profile.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def latest_raw_file() -> Path:
    raw_root = ROOT / "data" / "raw"
    if not raw_root.exists():
        raise FileNotFoundError("No raw data found")
    days = sorted([p for p in raw_root.iterdir() if p.is_dir()])
    if not days:
        raise FileNotFoundError("No dated raw directories found")
    latest_day = days[-1]
    fp = latest_day / "items.json"
    if not fp.exists():
        raise FileNotFoundError(f"Missing {fp}")
    return fp


def canonical_url(u: str) -> str:
    return u.split("?")[0].strip().lower()


def dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    out = []
    for it in items:
        key = canonical_url(it["url"])
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def freshness_score(published_str: str, decay_hours: float = 72.0) -> float:
    try:
        dt = dt_parser.parse(published_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except Exception:
        dt = datetime.now(timezone.utc)
    age_hours = max((datetime.now(timezone.utc) - dt).total_seconds() / 3600.0, 0)
    return math.exp(-age_hours / decay_hours)


def keyword_hits(text: str, keywords: list[str]) -> int:
    t = text.lower()
    return sum(1 for k in keywords if re.search(rf"\b{re.escape(k.lower())}\b", t))


def maturity_label(text: str) -> str:
    t = text.lower()
    if any(x in t for x in ["benchmark", "production", "release", "ga", "stable"]):
        return "production-ready"
    if any(x in t for x in ["preview", "beta", "experimental", "prototype"]):
        return "emerging"
    return "research"


def why_it_matters(item: dict[str, Any], tags: list[str]) -> str:
    if not tags:
        return "Potential relevance to AI platform stack; review for downstream impact."
    return f"Likely impact on {', '.join(tags[:3])} workflows and platform decisions."


def run():
    profile = load_profile()
    raw_file = latest_raw_file()

    with open(raw_file, "r", encoding="utf-8") as f:
        items = json.load(f)

    items = dedupe(items)

    pkw = profile.get("platform_keywords", [])
    hkw = profile.get("hype_keywords", [])
    w = profile.get("weights", {})
    decay = float(w.get("freshness_hours_decay", 72))

    scored = []
    for it in items:
        text = f"{it.get('title', '')} {it.get('summary', '')}"
        platform_hits = keyword_hits(text, pkw)
        hype_hits = keyword_hits(text, hkw)
        fresh = freshness_score(it.get("published", ""), decay)

        score = (
            float(it.get("source_weight", 1.0)) * float(w.get("source_weight", 1.0))
            + fresh
            + platform_hits * float(w.get("platform_relevance", 1.8))
            - hype_hits * float(w.get("hype_penalty", 0.8))
        )

        tags = [k for k in pkw if re.search(rf"\b{re.escape(k)}\b", text.lower())][:5]

        scored.append(
            {
                **it,
                "score": round(score, 3),
                "freshness": round(fresh, 3),
                "platform_hits": platform_hits,
                "hype_hits": hype_hits,
                "maturity": maturity_label(text),
                "tags": tags,
                "why_it_matters": why_it_matters(it, tags),
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)

    max_items = int(profile.get("max_digest_items", 10))
    min_score = float(profile.get("min_score", 1.0))
    top = [x for x in scored if x["score"] >= min_score][:max_items]

    processed_dir = ROOT / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    with open(processed_dir / "latest.json", "w", encoding="utf-8") as f:
        json.dump(top, f, ensure_ascii=False, indent=2)

    date_str = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# Daily AI SOTA Digest - {date_str}",
        "",
        "Focus: AI Platform Engineering",
        "",
    ]

    for i, it in enumerate(top, start=1):
        lines += [
            f"## {i}. {it['title']}",
            f"- Source: {it['source']}",
            f"- URL: {it['url']}",
            f"- Score: {it['score']} | Maturity: {it['maturity']}",
            f"- Tags: {', '.join(it['tags']) if it['tags'] else 'n/a'}",
            f"- Why it matters: {it['why_it_matters']}",
            "",
        ]

    digest_dir = ROOT / "data" / "digest"
    digest_dir.mkdir(parents=True, exist_ok=True)
    out = digest_dir / f"{date_str}.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).strip() + "\n")
    with open(digest_dir / "latest.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines).strip() + "\n")

    print(f"digest_items={len(top)} file={out}")


if __name__ == "__main__":
    run()
