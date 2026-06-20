"""Build "storylines" — stories that evolve across days — from the story store.

Flat feeds answer "what's new right now"; storylines answer "what happened
next with that thing from Tuesday". This script mechanically clusters the
durable story store (``pipeline/story_store.py``) over a trailing window into
cross-day threads, e.g. a model launch followed by hands-on posts, benchmark
threads, and pricing analysis.

Clustering is precision-first (a junk storyline costs reader trust, a missed
one costs nothing). First, re-syndicated copies of one story — the same
headline across sources, or the same Google-News article under different
redirect URLs — are collapsed into a single "node" (``dedup_nodes``) so an echo
can't inflate the item/day/source counts into a fake thread. Then two nodes
join the same thread when their titles share an anchor pair — two co-occurring
tokens of which at least one is "strong": rare in the window (document
frequency capped) and not a broad company/topic word (``WEAK``). Candidate
threads are merged when they share a strong anchor token (so "Claude Fable" and
"Fable Mythos" fold into one Fable 5 thread) or overlap heavily in members. A
cluster only becomes a storyline when it has enough items, spans multiple days,
and draws on multiple sources — single-day echo bursts and one-source columns
("Quoting …") don't qualify.

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
# Agent-written editorial narratives (see .agents/skills/storyline-editor). The
# pipeline only *reads* these and overlays them onto the served files below; it
# never writes them, so the editorial layer survives every recluster.
NARRATIVE_DIR = OUT_DIR / "narratives"
# Agent-confirmed thread links (see .agents/skills/storyline-scout) — the recall
# layer. Applied as synthetic candidates through the SAME floor as anchor pairs,
# so a link only surfaces if its nodes clear MIN_ITEMS/DAYS/SOURCES.
SCOUT_DIR = OUT_DIR / "scout"
LINKS_FILE = SCOUT_DIR / "links.json"
# Sentinel namespace for a scout candidate's key, kept out of the token space so
# it can never collide with (or be treated as) a real anchor token.
SCOUT_NS = "\x00scout"

WINDOW_DAYS = 21
MIN_ITEMS = 3
MIN_DAYS = 2
MIN_SOURCES = 2
# A confirmed scout link already carries its precision from the judge (a verified
# same-story link across sources), so the anchor-pair item-count noise-guard
# double-charges it. Scout links surface at a lower item floor than anchor pairs —
# but still must span multiple sources AND days, so a thin single-source or
# single-day link stays inert. The MIN_DAYS/MIN_SOURCES floor is unchanged.
SCOUT_MIN_ITEMS = 2
# A cluster absorbs a smaller candidate when they share this fraction of items.
MERGE_OVERLAP = 0.6
MAX_STORYLINES = 12

# Same-event re-syndication merge (dedup_nodes pass 3). A re-run of one story
# carries a shorter headline that is nearly a *subset* of the fuller one; a new
# storyline *beat* (release -> availability -> suspension) instead adds new
# significant tokens and falls below CONTAIN_MIN, so threads are never collapsed.
# Deliberately conservative — over-merging a distinct story costs reader trust.
NODE_CONTAIN_MIN = 0.8   # smaller significant-title set must be ~contained in the larger
NODE_MERGE_DAY_GAP = 2   # same news cycle — cross-source timestamps for one event drift a day or two
NODE_MERGE_MIN_TOKENS = 2  # never merge on a one-word title

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


def _uf(n: int):
    """Tiny union-find: returns (find, union) over n elements."""
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[max(ri, rj)] = min(ri, rj)

    return find, union


def dedup_nodes(recs: list[dict]) -> list[dict]:
    """Collapse re-syndications of one story into a single "node".

    The feed routinely carries the same headline from several sources, and the
    same Google-News article can resurface under different redirect URLs (hence
    different sids). Counting each copy as its own item silently manufactures
    multi-source, multi-day "storylines" out of a single event. We fold records
    that share a significant-title signature — its tokens minus grammar/hype
    noise (``title_tokens``) — into one node that carries every member's
    source/url but counts once.

    Two signatures also merge when the smaller (>=2 tokens) is a subset of the
    larger and the only extra tokens are broad company/topic words (``WEAK``),
    catching "Coding Agents Social Sciences" vs "... social sciences - Anthropic".

    A third pass folds same-event re-syndications that overlap heavily without
    being a clean subset — the shorter headline of a re-run is ~contained in the
    fuller one (``NODE_CONTAIN_MIN``) from a different source within a day. A
    storyline *beat* that adds new facts ("now available", "suspended") sits below
    the containment bar and is left as its own node, so threads survive dedup.
    Records whose significant title is empty stay singletons — never pool junk.
    """
    sig = [frozenset(title_tokens(r.get("title"))) for r in recs]
    find, union = _uf(len(recs))

    by_sig: dict[frozenset[str], list[int]] = defaultdict(list)
    for i, s in enumerate(sig):
        if s:
            by_sig[s].append(i)
    for idxs in by_sig.values():
        for j in idxs[1:]:
            union(idxs[0], j)
    for a, b in itertools.permutations(by_sig, 2):
        if len(a) >= 2 and a < b and (b - a) <= WEAK:
            union(by_sig[a][0], by_sig[b][0])

    # Pass 3: same-event re-syndications whose headlines overlap heavily but are
    # neither identical nor a weak-only superset — e.g. "Claude Fable 5 and Mythos
    # 5" (newsroom) vs "[AINews] … Claude Fable 5 — Mythos but Safe" (latent.space).
    # We fold a pair when the smaller significant-title set is ~contained in the
    # larger (NODE_CONTAIN_MIN), the two come from *different* sources within a day,
    # and they share a distinctive (non-WEAK) token. A storyline beat that adds new
    # facts ("now available", "suspended") lowers containment below the bar and is
    # left intact. Candidate pairs are gathered via distinctive-token buckets, so
    # records sharing only a broad company word are never even compared.
    by_tok: dict[str, list[int]] = defaultdict(list)
    for i, s in enumerate(sig):
        for tok in s:
            if tok not in WEAK:
                by_tok[tok].append(i)
    for idxs in by_tok.values():
        for i, j in itertools.combinations(idxs, 2):
            if find(i) == find(j):
                continue
            si, sj = sig[i], sig[j]
            small = si if len(si) <= len(sj) else sj
            if len(small) < NODE_MERGE_MIN_TOKENS:
                continue
            if len(si & sj) / len(small) < NODE_CONTAIN_MIN:
                continue
            ri, rj = recs[i], recs[j]
            if ri.get("source") and ri.get("source") == rj.get("source"):
                continue
            if abs((ri["_dt"].date() - rj["_dt"].date()).days) > NODE_MERGE_DAY_GAP:
                continue
            union(i, j)

    groups: dict[int, list[dict]] = defaultdict(list)
    for i, rec in enumerate(recs):
        groups[find(i)].append(rec)

    nodes = []
    for members in groups.values():
        rep = max(
            members,
            key=lambda r: (len(title_tokens(r.get("title"))), len(str(r.get("title") or ""))),
        )
        nodes.append({
            "items": members,
            "rep": rep,
            "title": rep.get("title") or "",
            "tokens": title_tokens(rep.get("title")),
            "_dt": min(r["_dt"] for r in members),
            "sources": sorted({r.get("source") for r in members if r.get("source")}),
            "sids": [r.get("sid") for r in members if r.get("sid")],
            "urls": [norm_url(r.get("url")) for r in members if r.get("url")],
        })
    nodes.sort(key=lambda n: n["_dt"])
    return nodes


def cluster(nodes: list[dict]) -> list[dict]:
    """Anchor-pair clustering over deduped nodes, then thread-merge.

    Two nodes join the same thread when their titles share an anchor pair — two
    co-occurring tokens of which at least one is "strong" (rare in the window
    and not a broad company/topic word). Candidate pairs that clear the
    item/day/source floor are then unioned into threads when they either share a
    strong anchor token — so "Claude Fable", "Fable Mythos" and "Fable access"
    fold into one Fable 5 thread instead of three — or overlap heavily in
    members (the fallback for threads bridged only by a weak-weak pair).
    """
    tokmap = [n["tokens"] for n in nodes]
    df = Counter(tok for toks in tokmap for tok in toks)
    rare_cap = max(5, round(len(nodes) * 0.02))

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
        days = {nodes[i]["_dt"].date() for i in idx}
        sources = {s for i in idx for s in nodes[i]["sources"]}
        if len(days) >= MIN_DAYS and len(sources) >= MIN_SOURCES:
            candidates.append({"key": key, "idx": set(idx), "scout": False})

    # Scout links → floor-gated synthetic candidates (the recall layer). Applied
    # through the SCOUT_MIN_ITEMS/MIN_DAYS/MIN_SOURCES floor (lower item floor than
    # anchor pairs — the judge supplies the precision), so a link is inert unless its
    # nodes clear it; no link bypasses the deterministic multi-source/multi-day gate.
    sid_to_nodes: dict[str, set[int]] = defaultdict(set)
    for ni, n in enumerate(nodes):
        for sid in n["sids"]:
            sid_to_nodes[sid].add(ni)
    scout_hint: dict[tuple[str, str], str] = {}
    for li, link in enumerate(load_links()):
        idx = {ni for sid in (link.get("members") or []) for ni in sid_to_nodes.get(sid, ())}
        if len(idx) < 2:
            continue
        days = {nodes[i]["_dt"].date() for i in idx}
        sources = {s for i in idx for s in nodes[i]["sources"]}
        if len(idx) >= SCOUT_MIN_ITEMS and len(days) >= MIN_DAYS and len(sources) >= MIN_SOURCES:
            key = (SCOUT_NS, str(link.get("id") or f"link-{li}"))
            candidates.append({"key": key, "idx": idx, "scout": True})
            scout_hint[key] = str(link.get("label_hint") or "")

    find, union = _uf(len(candidates))
    strong_tok = [
        set() if c["scout"] else {t for t in c["key"] if strong(t)} for c in candidates
    ]
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            ci, cj = candidates[i], candidates[j]
            if ci["scout"] or cj["scout"]:
                # An asserted link joins any candidate it shares a node with, so
                # it extends an existing thread instead of spawning a duplicate.
                if ci["idx"] & cj["idx"]:
                    union(i, j)
                continue
            if strong_tok[i] & strong_tok[j]:
                union(i, j)
                continue
            inter = len(ci["idx"] & cj["idx"])
            if inter and (
                inter / len(ci["idx"]) >= MERGE_OVERLAP
                or inter / len(cj["idx"]) >= MERGE_OVERLAP
            ):
                union(i, j)

    threads: dict[int, dict] = {}
    for i, c in enumerate(candidates):
        t = threads.setdefault(find(i), {"idx": set(), "keys": []})
        t["idx"] |= c["idx"]
        t["keys"].append(c["key"])

    clusters = []
    for t in threads.values():
        anchor_keys = [k for k in t["keys"] if k[0] != SCOUT_NS]
        hints = [scout_hint[k] for k in t["keys"] if k[0] == SCOUT_NS]
        # Primary key (drives the label) = the anchor pair covering most nodes;
        # a scout-only thread falls back to the link's label hint.
        keys = sorted(anchor_keys, key=lambda k: (-len(pair_items[k]), k))
        clusters.append({
            "items": sorted((nodes[i] for i in t["idx"]), key=lambda n: n["_dt"]),
            "keys": keys,
            "via_scout": bool(hints),
            "scout_hint": next((h for h in hints if h), ""),
        })
    return clusters


def load_links() -> list[dict]:
    """Agent-confirmed scout links. Tolerates a bare list or a {"links": [...]}
    wrapper; drops anything without a ``members`` list."""
    data = load_json(LINKS_FILE, [])
    if isinstance(data, dict):
        data = data.get("links", [])
    if not isinstance(data, list):
        return []
    return [l for l in data if isinstance(l, dict) and isinstance(l.get("members"), list)]


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
        sids = {sid for n in c["items"] for sid in n["sids"]}
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


ITEM_FIELDS = ("title", "url", "source", "type", "summary_1line", "why_it_matters")


def timeline_item(node: dict) -> dict:
    """One timeline card per deduped node. ``sources`` is set only when the
    story ran in more than one place, so the page can badge "also covered by"
    instead of repeating the same card per source."""
    rep = node["rep"]
    out = {k: rep[k] for k in ITEM_FIELDS if rep.get(k)}
    out["sid"] = node["sids"][0] if node["sids"] else rep.get("sid")
    out["url"] = norm_url(rep.get("url"))
    out["published"] = node["_dt"].isoformat()
    if len(node["sources"]) > 1:
        out["sources"] = node["sources"]
    return out


def apply_narrative(slug: str, detail: dict, entry: dict) -> None:
    """Overlay an agent-written narrative sidecar onto the served storyline.

    Mutates ``detail`` (the per-slug timeline file) and ``entry`` (the index
    row) in place. Adds an ``editorial`` block (TL;DR arc / what's-new /
    why-it-matters) and a per-item ``editor_note``; the index row gets a TL;DR
    teaser. Deterministic JSON read + merge — no LLM here. A narrative whose
    snapshot no longer matches the thread is still shown but flagged
    ``stale: true`` so the page (and the editor routine) can tell it predates
    the latest update.
    """
    narr = load_json(NARRATIVE_DIR / f"{slug}.json", None)
    tldr = narr.get("tldr") if isinstance(narr, dict) else None
    if not tldr:
        return

    current_sids = set(entry.get("member_sids") or [])
    fresh = (
        narr.get("covers_last_updated") == entry.get("last_updated")
        and set(narr.get("covers_member_sids") or []) == current_sids
    )
    editorial = {"tldr": tldr, "stale": not fresh}
    for k in ("whats_new", "why_it_matters", "take_for_builders"):
        if narr.get(k):
            editorial[k] = narr[k]
    # Arc layer: status banner, narrative beats, and "what to watch" questions.
    # Beats reference member sids; drop any that no longer belong to the thread
    # so the overlay can never point a beat at a reclustered-away item.
    if isinstance(narr.get("status"), dict):
        editorial["status"] = narr["status"]
    beats = narr.get("beats")
    if isinstance(beats, list):
        clean = []
        for b in beats:
            if not isinstance(b, dict):
                continue
            sids = [s for s in (b.get("sids") or []) if s in current_sids]
            clean.append({**b, "sids": sids})
        if clean:
            editorial["beats"] = clean
    oq = narr.get("open_questions")
    if isinstance(oq, list):
        editorial["open_questions"] = [str(q) for q in oq if str(q).strip()]
    # Per-item agent provenance (scout / fact-checker / watcher badges), keyed
    # by sid — keep only sids still in the thread.
    prov = narr.get("provenance")
    if isinstance(prov, dict):
        kept = {s: v for s, v in prov.items() if s in current_sids and isinstance(v, dict)}
        if kept:
            editorial["provenance"] = kept
    if narr.get("generated_at"):
        editorial["generated_at"] = narr["generated_at"]

    detail["editorial"] = editorial
    # Index row carries a teaser plus the status pill so /storylines can badge it.
    entry["editorial"] = {"tldr": tldr, "stale": not fresh}
    if isinstance(narr.get("status"), dict):
        entry["editorial"]["status"] = narr["status"]

    captions = narr.get("day_captions") or {}
    if isinstance(captions, dict):
        for day in detail.get("days") or []:
            for it in day.get("items") or []:
                note = captions.get(it.get("sid"))
                if note:
                    it["editor_note"] = note


def build() -> dict:
    now = datetime.now(timezone.utc)
    recs = load_window(now)
    nodes = dedup_nodes(recs)
    clusters = cluster(nodes)
    for c in clusters:
        # Anchor pair drives the label; a scout-only thread has no anchor key, so
        # fall back to the link's label hint (then the latest title).
        if c["keys"]:
            c["label"] = cluster_label(c["items"], c["keys"])
        else:
            c["label"] = c.get("scout_hint") or (c["items"][-1].get("title") or "Storyline")
    # Most recently updated storylines first; cap to keep the page focused.
    clusters.sort(key=lambda c: c["items"][-1]["_dt"], reverse=True)
    clusters = clusters[:MAX_STORYLINES]
    carry_over_slugs(clusters)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index_entries = []
    for c in clusters:
        items = c["items"]
        days = sorted({n["_dt"].date().isoformat() for n in items})
        sources = sorted({s for n in items for s in n["sources"]})
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
        if c.get("via_scout"):
            common["via_scout"] = True
        entry = {
            **common,
            "latest_title": latest.get("title") or "",
            "days": days,
            # Flattened across deduped members so the feed badges every URL/sid
            # that belongs to the thread, not just the representative copy.
            "member_sids": [sid for n in items for sid in n["sids"]],
            "member_urls": [u for n in items for u in n["urls"]],
        }

        by_day: dict[str, list[dict]] = defaultdict(list)
        for n in items:
            by_day[n["_dt"].date().isoformat()].append(timeline_item(n))
        detail = {
            **common,
            "generated_at": now.isoformat(),
            "sources": sources,
            "days": [{"date": d, "items": by_day[d]} for d in days],
        }
        # Overlay the durable agent-written narrative (if any) onto both the
        # detail file and its index row, so editorial work survives reclusters.
        apply_narrative(c["slug"], detail, entry)
        index_entries.append(entry)
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
