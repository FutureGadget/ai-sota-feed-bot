#!/usr/bin/env python3
"""Build the frozen Jev quality benchmark from committed raw snapshots.

The benchmark is a small, stratified sample of the candidate pool: good
first-party engineering, marketing, practitioner analysis, search SEO, search
business/gossip, off-topic domain science, research, and release notes. Labels
are provisional (assistant-authored) until the owner reviews them.

Usage:
    python3 scripts/build_quality_benchmark.py
    python3 scripts/build_quality_benchmark.py --check
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from editorial import load_config as load_editorial_config, source_role  # noqa: E402

RAW_DIR = ROOT / "data" / "raw"
OUT_FILE = ROOT / "data" / "quality" / "benchmark" / "items.json"
LABELS_FILE = ROOT / "data" / "quality" / "benchmark" / "labels.md"
CACHE_FILE = ROOT / "data" / "quality" / "benchmark" / "content_cache.json"
# The video slice is frozen from the real YouTube/podcast feeds rather than
# built from data/raw: a two-hour build only keeps a fresh edition, and the
# transcript digests are not article paragraphs. Both files are committed, so
# the benchmark is reproducible offline.
VIDEO_FILE = ROOT / "data" / "quality" / "benchmark" / "video_items.json"
MIN_DATE = "2026-09-15"
EXCERPT_CHARS = 2500

# (slice, source, title prefix, expected binary, fine label, note)
SELECTIONS: list[tuple[str, str, str, str, str, str]] = [
    # First-party engineering. These should survive a quality gate.
    ("first_party_engineering", "anthropic_engineering", "Redesigning source control at Anthropic", "keep", "must_read",
     "First-party engineering deep dive on source control at a frontier lab."),
    ("first_party_engineering", "cloudflare_blog", "Cutting our inference bill by 68%", "keep", "must_read",
     "Concrete inference cost optimization with numbers; direct platform-engineer fit."),
    ("first_party_engineering", "vllm_blog", "GLM-5.3 Optimizations, Part 2", "keep", "must_read",
     "Deep inference serving optimization detail (PCP, DCP, HiSparse) with hardware context."),
    ("first_party_engineering", "huggingface_blog", "How Specializing the Vocabulary of SLMs Can Cut Inference Cost by 77%", "keep", "useful",
     "Concrete inference-cost technique with a measured result."),
    ("first_party_engineering", "claude_dev_blog", "How the Claude Code team does code review", "keep", "useful",
     "Engineering practice from the team building a coding agent."),
    ("first_party_engineering", "google_cloud_blog", "Who judges the judge? Three helpful ways to audit your LLM evaluators", "keep", "must_read",
     "Eval auditing guidance; directly relevant to the judge layer we are building."),

    # First-party marketing/corporate. Mostly drop, with two hard positives:
    # a relevant product availability post and a relevant agent-skills donation.
    ("first_party_marketing", "openai_blog", "ChatGPT Ads expands to 26 new countries", "drop", "junk",
     "Ad-market expansion; no engineering substance for the platform-engineer lens."),
    ("first_party_marketing", "openai_blog", "How AT&T is rethinking in-house legal work", "drop", "junk",
     "Customer story about legal work; no reusable platform mechanism."),
    ("first_party_marketing", "openai_blog", "OpenAI and Poland", "drop", "junk",
     "Government partnership announcement; no technical detail."),
    ("first_party_marketing", "anthropic_newsroom", "2026 Usage Policy update", "drop", "junk",
     "Policy update; not engineering content."),
    ("first_party_marketing", "anthropic_newsroom", "Singapore office and government MOU", "drop", "junk",
     "Office/MOU announcement; no engineering content."),
    ("first_party_marketing", "modal_blog", "Modal crosses $1B in Annualized Run Rate", "drop", "junk",
     "Funding/ARR announcement; company news, not engineering."),
    ("first_party_marketing", "openai_blog", "OpenAI models are coming to Google Cloud", "keep", "useful",
     "Hard positive: a distribution announcement that changes where platform teams can run the model."),
    ("first_party_marketing", "anthropic_newsroom", "Donating Agent Skills to the Agentic AI Foundation", "keep", "useful",
     "Hard positive: a corporate announcement about agent skills that is directly relevant to agent builders."),

    # Practitioner analysis. Mostly keep, with off-topic link-blog items as drops.
    ("practitioner_analysis", "simon_willison", "Introducing Kimi K3.1 Pro", "keep", "useful",
     "Launch analysis with model details from a trusted practitioner."),
    ("practitioner_analysis", "latent_space", "[AINews] Kimi 3.1 Pro 104BA-2.8T", "keep", "must_read",
     "Detailed open-weight model analysis with benchmark and pricing context."),
    ("practitioner_analysis", "hamel_husain", "How To Use Decision Models for Evals", "keep", "must_read",
     "Directly relevant to the Jev/decision-model judge design."),
    ("practitioner_analysis", "infoq_ai_ml", "Google’s Data Agent Kit Hits GA", "keep", "useful",
     "Agent platform release with an architecture angle (skills vs IAM guardrails)."),
    ("practitioner_analysis", "simon_willison", "Today's PHP Security Release", "drop", "filler",
     "Off-mission PHP security release; no AI/agent engineering substance."),
    ("practitioner_analysis", "simon_willison", "Panache", "drop", "junk",
     "Off-mission game/RTS post; no AI platform relevance."),

    # Search SEO. One hard positive: a genuine launch scoop, not a comparison.
    ("search_seo", "search_agent_engineering_news", "Claude Code vs Codex vs Copilot", "drop", "junk",
     "SEO comparison listicle; no original engineering evidence."),
    ("search_seo", "search_agent_engineering_news", "7 Best Claude Code Alternatives", "drop", "junk",
     "Ranked listicle; no substantive mechanism."),
    ("search_seo", "search_agent_engineering_news", "Best AI Coding Agent in 2026", "drop", "junk",
     "Buyer's-guide listicle; not platform engineering."),
    ("search_seo", "search_cn_open_weight_labs", "What Is DeepSeek?", "drop", "junk",
     "Explainer/SEO content; no new information."),
    ("search_seo", "search_cn_open_weight_labs", "DeepSeek API Key Setup", "drop", "junk",
     "Step-by-step setup SEO; not engineering analysis."),
    ("search_seo", "search_cn_open_weight_labs", "DeepSeek Ships a Faster Flash Model", "keep", "useful",
     "Hard positive: a genuine release scoop with a concrete API change."),

    # Search business/gossip. One hard positive: a real API/pricing change.
    ("search_business_gossip", "search_cn_open_weight_labs", "China's Teenage AI Prodigy", "drop", "junk",
     "Executive/gossip story; no engineering substance."),
    ("search_business_gossip", "search_cn_open_weight_labs", "DeepSeek Raises $15 Billion Ahead of Planned Shanghai IPO", "drop", "junk",
     "Funding/IPO story; no engineering substance."),
    ("search_business_gossip", "search_cn_open_weight_labs", "DeepSeek fires back at U.S.", "drop", "junk",
     "Policy/market reaction; no engineering substance."),
    ("search_business_gossip", "search_cn_open_weight_labs", "DeepSeek Suffers Nearly 5-Hour Outage", "drop", "junk",
     "Outage story without a technical postmortem; not actionable."),
    ("search_business_gossip", "search_cn_open_weight_labs", "Alibaba starts selling its Qwen N1 AI glasses", "drop", "junk",
     "Consumer hardware/PR; off-mission."),
    ("search_business_gossip", "search_cn_open_weight_labs", "DeepSeek prices web search for AI agents", "keep", "useful",
     "Hard positive: a concrete API pricing change for agent builders."),

    # Off-topic domain science. Should be dropped unless a serving/inference lesson is present.
    ("off_topic_domain", "google_deepmind_blog", "Accelerating the search for antimicrobial peptides", "drop", "junk",
     "Domain science (antimicrobial peptides); no platform-engineering lesson."),
    ("off_topic_domain", "openai_blog", "Using thousands of AI agents to uncover new leads in biological data", "drop", "filler",
     "Agent use case in biology; interesting, but not platform-engineering guidance."),
    ("off_topic_domain", "arxiv_llm_reliability", "IndoNutriQA", "drop", "junk",
     "Clinical nutrition benchmark; off-mission."),
    ("off_topic_domain", "google_deepmind_blog", "Beyond tree cover", "drop", "junk",
     "Forest mapping; no agent/platform engineering."),
    ("off_topic_domain", "databricks_blog", "Deploy RFD4-Proteina", "drop", "junk",
     "Protein model deployment; domain science, not platform guidance."),
    ("off_topic_domain", "latent_space", "AI Is Getting Good at Math", "drop", "junk",
     "Math capability commentary; no platform-engineering mechanism."),

    # Research. Mostly keep if it is agent/inference/eval research.
    ("research", "arxiv_agent_systems_research", "Muffin - A Shared Memory Buffer", "keep", "useful",
     "Agent memory architecture with a concrete mechanism."),
    ("research", "arxiv_agent_systems_research", "Post-Audit Mirage", "keep", "useful",
     "Limits of offline agent verification; relevant to eval design."),
    ("research", "arxiv_cs_ai", "Adaptive Skill Granularity for Coding Agents", "keep", "useful",
     "Runtime routing and recovery for coding agents; directly relevant."),
    ("research", "arxiv_cs_ai", "Causal Chain of Thought", "keep", "useful",
     "Context isolation and attention leakage; relevant to agent reliability."),
    ("research", "arxiv_llm_reliability", "When LLMs Forget What They Believe", "keep", "useful",
     "Long-horizon state integrity; relevant to agent memory/reliability."),
    ("research", "arxiv_cs_cl", "Parameter-Efficient Adaptation of Large Language Models to a Low-Resource", "drop", "filler",
     "Niche low-resource adaptation; not platform/agent engineering."),

    # Releases. Release notes are drop for the brief; substantive release posts are keep.
    ("releases", "vllm_releases", "v0.32.0", "drop", "filler",
     "Routine release notes; belongs in the Releases tab, not the brief."),
    ("releases", "claude_code_releases", "v2.1.310", "drop", "filler",
     "Routine CLI version bump; no standalone engineering insight."),
    ("releases", "langgraph_releases", "langgraph==1.2.17", "drop", "filler",
     "Routine package release; no standalone engineering insight."),
    ("releases", "openai_codex_releases", "0.164.0-alpha", "drop", "filler",
     "Alpha release note; no standalone engineering insight."),
    ("releases", "huggingface_blog", "Welcome Beam", "keep", "useful",
     "Model release with serving/deployment context; useful to platform teams."),
    ("releases", "vllm_blog", "vLLM Delivers Day-0 Support for MiniMax-M3.1-Flash", "keep", "useful",
     "Serving support for a new model; useful to inference-platform teams."),
]


def _clean_excerpt(value: str, limit: int = EXCERPT_CHARS) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<script\b.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit].rstrip()


def _load_video_items() -> list[dict]:
    if not VIDEO_FILE.exists():
        return []
    try:
        payload = json.loads(VIDEO_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    return [row for row in payload if isinstance(row, dict)] if isinstance(payload, list) else []


def _load_content_cache() -> dict[str, str]:
    if not CACHE_FILE.exists():
        return {}
    try:
        payload = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _save_content_cache(cache: dict[str, str]) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _is_textual(text: str) -> bool:
    if len(text) < 100:
        return False
    printable = sum(1 for ch in text if ch.isprintable() or ch in "\n\t")
    return (printable / max(1, len(text))) >= 0.85


def _should_fetch(item: dict) -> bool:
    source = str(item.get("source") or "")
    url = str(item.get("url") or "")
    if source.startswith("search_") or "news.google.com" in url:
        return False
    if "/releases/tag/" in url or source.endswith("_releases"):
        return False
    if source.startswith("arxiv_") or "arxiv.org" in url:
        return False
    return True


def _fetch_paragraph_text(url: str, timeout: int = 10, max_chars: int = EXCERPT_CHARS) -> str:
    """Extract the article's paragraphs, skipping nav and tag-cloud boilerplate."""
    import urllib.request

    sys.path.insert(0, str(ROOT / "pipeline"))
    from content_fetch import _fetch_text  # noqa: E402

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) OpenClawFeedBot/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read(800_000).decode("utf-8", errors="ignore")
    paragraphs = []
    for match in re.findall(r"<p\b[^>]*>(.*?)</p>", raw, re.I | re.S):
        text = re.sub(r"<[^>]+>", " ", match)
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) < 80:
            continue
        lowered = text.lower()
        if any(
            marker in lowered
            for marker in (
                "cookie",
                "subscribe to",
                "sign up for",
                "all rights reserved",
                "privacy policy",
                "skip to content",
                "follow us",
                "share this",
            )
        ):
            continue
        paragraphs.append(text)
        if sum(len(p) for p in paragraphs) >= max_chars:
            break
    text = " ".join(paragraphs)[:max_chars].strip()
    if len(text) < 300:
        return _clean_excerpt(_fetch_text(url, timeout=timeout, max_bytes=600_000), max_chars)
    return text


def _enrich_excerpt(item: dict, cache: dict[str, str], fetch: bool) -> tuple[str, str]:
    raw = _clean_excerpt(item.get("content_excerpt") or item.get("summary") or "")
    url = str(item.get("url") or "").split("#")[0]
    if len(raw) >= 800:
        return raw, "raw_excerpt"
    if url in cache:
        cached = cache[url]
        if _is_textual(cached):
            return cached[:EXCERPT_CHARS], "cache"
        cache.pop(url, None)
    if not fetch or not _should_fetch(item):
        return raw or _clean_excerpt(item.get("summary_1line") or item.get("summary") or ""), "title_summary"
    try:
        sys.path.insert(0, str(ROOT / "pipeline"))
        from content_fetch import _fetch_text  # noqa: E402

        text = _fetch_paragraph_text(url, timeout=8, max_chars=EXCERPT_CHARS)
        text = _clean_excerpt(text)
        if _is_textual(text) and len(text) > len(raw):
            cache[url] = text
            return text, "fetched_paragraphs"
    except Exception as exc:
        print(f"fetch_failed url={url} err={exc}", file=sys.stderr)
    return raw or _clean_excerpt(item.get("summary_1line") or item.get("summary") or ""), "title_summary"


def _load_raw_items() -> list[dict]:
    items: list[dict] = []
    for path in sorted(RAW_DIR.glob("*/items.json")):
        date = path.parent.name
        if date < MIN_DATE:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        rows = payload if isinstance(payload, list) else payload.get("items", [])
        for row in rows:
            if not isinstance(row, dict):
                continue
            row = dict(row)
            row["_raw_date"] = date
            items.append(row)
    return items


def _find(items: list[dict], source: str, prefix: str) -> dict | None:
    prefix_lower = prefix.lower()
    matches = [
        item for item in items
        if item.get("source") == source
        and str(item.get("title") or "").lower().startswith(prefix_lower)
    ]
    if not matches:
        return None
    # Newest raw date wins; within a date, the first row is fine.
    matches.sort(key=lambda item: item.get("_raw_date", ""), reverse=True)
    return matches[0]


def build(check: bool = False, fetch: bool = False) -> int:
    editorial_cfg = load_editorial_config()
    items = _load_raw_items()
    content_cache = _load_content_cache()
    out = []
    missing = []
    for idx, (slice_name, source, prefix, expected, fine, note) in enumerate(SELECTIONS, start=1):
        found = _find(items, source, prefix)
        if not found:
            missing.append((slice_name, source, prefix))
            continue
        excerpt, excerpt_source = _enrich_excerpt(found, content_cache, fetch)
        out.append(
            {
                "id": f"bench-{idx:03d}",
                "slice": slice_name,
                "source": source,
                "source_role": source_role(source, editorial_cfg),
                "title": found.get("title") or "",
                "url": found.get("url") or "",
                "published": found.get("published") or "",
                "raw_date": found.get("_raw_date") or "",
                "summary_1line": found.get("summary_1line") or "",
                "excerpt": excerpt,
                "excerpt_source": excerpt_source,
                "expected": expected,
                "expected_label": fine,
                "notes": note,
            }
        )

    video_items = _load_video_items()
    for offset, row in enumerate(video_items, start=len(out) + 1):
        item = dict(row)
        item["id"] = f"bench-{offset:03d}"
        item.setdefault("source_role", source_role(str(item.get("source") or ""), editorial_cfg))
        item.setdefault("summary_1line", "")
        item.setdefault("excerpt_source", "video_transcript")
        out.append(item)

    if missing:
        print("MISSING selections:", file=sys.stderr)
        for row in missing:
            print("  ", row, file=sys.stderr)
        return 1

    if check:
        print(f"benchmark_ok items={len(out)} slices={len({i['slice'] for i in out})}")
        return 0

    _save_content_cache(content_cache)
    payload = {
        "benchmark_version": "jev-feed-quality-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rubric": {
            "task": "Decide whether this item belongs in the default Brief lens for AI platform and agent engineers.",
            "keep": "must_read or useful: substantive, original, relevant, and actionable enough to spend reading time on.",
            "drop": "filler or junk: marketing, customer stories, SEO listicles, gossip, off-mission domain science, routine release notes.",
            "fine_labels": ["must_read", "useful", "filler", "junk"],
        },
        "items": out,
    }
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Benchmark labels (provisional)",
        "",
        "Assistant-authored labels for owner review. Edit `items.json` after",
        "correcting a row, then rerun the benchmark.",
        "",
        "| id | slice | source | title | expected | fine | note |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in out:
        title = str(item["title"]).replace("|", "\\|")
        note = str(item["notes"]).replace("|", "\\|")
        lines.append(
            f"| {item['id']} | {item['slice']} | {item['source']} | {title} | {item['expected']} | {item['expected_label']} | {note} |"
        )
    LABELS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT_FILE} items={len(out)}")
    print(f"wrote {LABELS_FILE}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate selections without writing")
    parser.add_argument("--fetch", action="store_true", help="fetch missing article bodies (cached)")
    args = parser.parse_args()
    raise SystemExit(build(check=args.check, fetch=args.fetch))


if __name__ == "__main__":
    main()
