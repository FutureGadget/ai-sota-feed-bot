"""Build "storylines" — stories that evolve across days — from the story store.

Flat feeds answer "what's new right now"; storylines answer "what happened
next with that thing from Tuesday". This script mechanically clusters the
durable story store (``pipeline/story_store.py``) over a trailing window into
cross-day threads, e.g. a model launch followed by hands-on posts, benchmark
threads, and pricing analysis.

Clustering is precision-first (a junk storyline costs reader trust, a missed
one costs nothing): two stories join the same thread only when their titles
share an anchor pair — two co-occurring tokens of which at least one is
"strong": rare in the window (document frequency capped) and not a broad
company/topic word (``WEAK``). A cluster only becomes a storyline when it has
enough items, spans multiple days, and draws on multiple sources — single-day
echo bursts and one-source columns ("Quoting …") don't qualify.

Outputs (consumed by ``api/storylines.js`` and the /storyline pages):

- ``data/storylines/index.json``   active storylines in the window, with the
  member URLs + dates the feed UI needs to badge cards client-side
- ``data/storylines/<slug>.json``  full day-by-day timeline per storyline

Detail files are never pruned: shared /storyline/<slug> links must keep
working after the thread ages out of the index window. Slugs are carried
over between runs by member overlap so follows survive recluster jitter.

Stdlib only, like the rest of the pipeline. Run after ``story_store.py sync``:

    python pipeline/build_storylines.py
"""

from __future__ import annotations

import itertools
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from story_store import load_store, norm_url, parse_dt

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "storylines"

WINDOW_DAYS = 21
MIN_ITEMS = 3
MIN_DAYS = 2
MIN_SOURCES = 2
# A cluster absorbs a smaller candidate when they share this fraction of items.
MERGE_OVERLAP = 0.6
MAX_STORYLINES = 12

TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.\-']*")

# Title noise: grammar, hype verbs, calendar words, and feed-speak that never
# identify a specific story.
STOP = set(
    """a an the and or of for to in on with from by at as is are was were be been being via
    about into over under after behind without before between against beyond per off up down out
    new news how why what when where which your you we i it its his her they them this that these
    those vs versus using use used uses guide intro introducing announcing announce announced
    announces release released releases releasing launch launches launched launching version
    update updates updated upgrade available now today week month year next first last latest big
    small better best top more less most ai llm llms genai model models agent agents agentic open
    source opensource data show hn ask built build builds building run runs running code coding
    developer developers dev devs january february march april may june july august september
    october november december monthly weekly daily newsletter edition issue series part one two
    three adds add ships ship gets get says say can will just still real really every all some no
    not none than then there here our help make makes making meet article presentation quoting
    tool tools platform platforms app apps api apis service services feature features support
    inside works working work way ways things thing time times day days like good great need
    needs needed want wants do does did done go goes going come comes coming back ainews""".split()
)

# Real words, but too broad to anchor a storyline on their own ("openai" or
# "inference" name a beat, not an event). They may still be the second half
# of an anchor pair next to a strong token ("claude fable", "rtx spark").
WEAK = set(
    """openai anthropic google microsoft meta nvidia aws azure amazon apple oracle cisco ibm
    intel claude gemini gpt chatgpt llama copilot grok mistral deepseek qwen gemma hugging face
    huggingface github inference reasoning benchmark benchmarks training eval evals evaluation
    mcp cli rag multi-agent orchestration workflow workflows context memory search engineering
    enterprise research security safety performance scale local browser terminal desktop mobile
    cloud robotics video voice vision language frontier compute infra infrastructure stack
    pipeline prompt prompts token tokens""".split()
)


def title_tokens(title) -> set[str]:
    out = set()
    for word in TOKEN_RE.findall(str(title or "")):
        tok = word.lower().strip(".-'")
        if len(tok) >= 3 and tok not in STOP and not tok.isdigit():
            out.add(tok)
    return out


def record_dt(rec: dict) -> datetime | None:
    return parse_dt(rec.get("published")) or parse_dt(rec.get("first_seen"))


def load_window(now: datetime) -> list[dict]:
    cutoff = now - timedelta(days=WINDOW_DAYS)
    recs = []
    for rec in load_store().values():
        dt = record_dt(rec)
        if dt and dt >= cutoff and rec.get("title") and rec.get("url"):
            rec = dict(rec)
            rec["_dt"] = dt
            recs.append(rec)
    recs.sort(key=lambda r: r["_dt"])
    return recs


def cluster(recs: list[dict]) -> list[dict]:
    """Anchor-pair clustering; returns [{"items": [rec], "keys": [(a, b)]}]."""
    tokmap = [title_tokens(r.get("title")) for r in recs]
    df = Counter(tok for toks in tokmap for tok in toks)
    rare_cap = max(5, round(len(recs) * 0.02))

    def strong(tok: str) -> bool:
        return tok not in WEAK and df[tok] <= rare_cap

    pair_items: dict[tuple[str, str], set[int]] = defaultdict(set)
    for i, toks in enumerate(tokmap):
        for a, b in itertools.combinations(sorted(toks), 2):
            if strong(a) or strong(b):
                pair_items[(a, b)].add(i)

    candidates = []
    for key, idx in pair_items.items():
        if len(idx) < MIN_ITEMS:
            continue
        days = {recs[i]["_dt"].date() for i in idx}
        sources = {recs[i].get("source") for i in idx}
        if len(days) >= MIN_DAYS and len(sources) >= MIN_SOURCES:
            candidates.append((key, idx))

    clusters: list[dict] = []
    for key, idx in sorted(candidates, key=lambda kv: (-len(kv[1]), kv[0])):
        for c in clusters:
            inter = len(idx & c["idx"])
            if inter and (inter / len(idx) >= MERGE_OVERLAP or inter / len(c["idx"]) >= MERGE_OVERLAP):
                c["idx"] |= idx
                c["keys"].append(key)
                break
        else:
            clusters.append({"idx": set(idx), "keys": [key]})

    return [
        {"items": sorted((recs[i] for i in c["idx"]), key=lambda r: r["_dt"]), "keys": c["keys"]}
        for c in clusters
    ]


def cluster_label(items: list[dict], keys: list[tuple[str, str]]) -> str:
    """Display label from the primary anchor pair, in natural title order and
    casing — e.g. ("fable", "claude") + "Initial impressions of Claude Fable 5"
    -> "Claude Fable"."""
    a, b = keys[0]
    for rec in items:
        words = TOKEN_RE.findall(str(rec.get("title") or ""))
        pos = {}
        for i, w in enumerate(words):
            tok = w.lower().strip(".-'")
            if tok in (a, b) and tok not in pos:
                pos[tok] = (i, w)
        if len(pos) == 2:
            ordered = sorted(pos.values())
            return " ".join(w if w[:1].isupper() else w.capitalize() for _, w in ordered)
    return f"{a.capitalize()} {b.capitalize()}"


def slugify(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    return slug or "storyline"


def load_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def carry_over_slugs(clusters: list[dict]) -> None:
    """Reuse the previous run's slug for the cluster sharing the most members,
    so follows and shared links survive recluster jitter."""
    prev = load_json(OUT_DIR / "index.json", {})
    prev_members = {
        s["slug"]: set(s.get("member_sids") or [])
        for s in (prev.get("storylines") or [])
        if isinstance(s, dict) and s.get("slug")
    }
    taken = set()
    for c in clusters:
        sids = {r.get("sid") for r in c["items"]}
        best, best_n = None, 0
        for slug, members in prev_members.items():
            n = len(sids & members)
            if slug not in taken and n > best_n:
                best, best_n = slug, n
        if best and best_n >= 2:
            c["slug"] = best
            taken.add(best)
    for c in clusters:
        if "slug" not in c:
            slug = slugify(c["label"])
            while slug in taken:
                slug += "-" + c["items"][0]["_dt"].strftime("%Y-%m-%d")
            c["slug"] = slug
            taken.add(slug)


ITEM_FIELDS = ("sid", "title", "url", "source", "type", "published", "summary_1line", "why_it_matters")


def timeline_item(rec: dict) -> dict:
    out = {k: rec[k] for k in ITEM_FIELDS if rec.get(k)}
    out["published"] = rec["_dt"].isoformat()
    return out


def build() -> dict:
    now = datetime.now(timezone.utc)
    recs = load_window(now)
    clusters = cluster(recs)
    for c in clusters:
        c["label"] = cluster_label(c["items"], c["keys"])
    # Most recently updated storylines first; cap to keep the page focused.
    clusters.sort(key=lambda c: c["items"][-1]["_dt"], reverse=True)
    clusters = clusters[:MAX_STORYLINES]
    carry_over_slugs(clusters)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index_entries = []
    for c in clusters:
        items = c["items"]
        days = sorted({r["_dt"].date().isoformat() for r in items})
        sources = sorted({r.get("source") for r in items if r.get("source")})
        latest = items[-1]
        common = {
            "slug": c["slug"],
            "label": c["label"],
            "item_count": len(items),
            "day_count": len(days),
            "source_count": len(sources),
            "first_seen": items[0]["_dt"].isoformat(),
            "last_updated": latest["_dt"].isoformat(),
        }
        index_entries.append({
            **common,
            "latest_title": latest.get("title") or "",
            "days": days,
            "member_sids": [r.get("sid") for r in items],
            "member_urls": [norm_url(r.get("url")) for r in items],
        })

        by_day: dict[str, list[dict]] = defaultdict(list)
        for r in items:
            by_day[r["_dt"].date().isoformat()].append(timeline_item(r))
        detail = {
            **common,
            "generated_at": now.isoformat(),
            "sources": sources,
            "days": [{"date": d, "items": by_day[d]} for d in days],
        }
        (OUT_DIR / f"{c['slug']}.json").write_text(
            json.dumps(detail, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )

    index = {
        "generated_at": now.isoformat(),
        "window_days": WINDOW_DAYS,
        "storylines": index_entries,
    }
    (OUT_DIR / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    return index


def main() -> None:
    index = build()
    lines = [f"storylines: {len(index['storylines'])} (window {index['window_days']}d)"]
    for s in index["storylines"]:
        lines.append(
            f"  - {s['slug']}: {s['item_count']} items / {s['day_count']} days"
            f" / {s['source_count']} sources — {s['label']}"
        )
    print("\n".join(lines))


if __name__ == "__main__":
    main()
