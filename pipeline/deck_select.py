"""Budgeted story selection for the editor decks.

Input: judged candidates from ``pipeline/deck_candidates.py``.
Output: a ranked ``shortlist`` and a ``bench`` for a deck (daily, weekly, ...).

1. Collapse candidates to one card per story (``story_key``, else URL),
   then join stories that name the same model at the same version
   (``kimi|3.1``). Coverage (distinct sources across the merged story)
   becomes a utility signal.
2. Score each story with the weights in ``config/decks.yaml``.
3. Solve a min-cost flow:

       S -> role_r       cap = per-role cap (source role: research, ...)
       role_r -> source  cap = per-source cap
       source_j -> item  cap 1, cost = -utility
       item -> category  cap 1
       category -> T     floor edge (cap = min, large bonus) + rest edge
                         (cap = max - min)
       total flow <= budget

   Items below ``min_utility`` get no edge, and the solver stops when one
   more story would not raise total utility, so a quiet window yields a
   shorter list instead of filler.

Each item has exactly one source and one category, and each source one
role, so this is an exact selection under nested source/role caps on one side
and category caps on the other (a greedy pick is not
optimal once both bind). Everything is deterministic.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

try:
    from mincostflow import MinCostFlow
except Exception:  # pragma: no cover
    from pipeline.mincostflow import MinCostFlow

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "decks.yaml"

SCALE = 1000  # utility -> integer cost
FLOOR_BONUS = 10**9
RELEASE_CATEGORY = "release_note"
UNCATEGORIZED = "uncategorized"


def load_config(path: Path | None = None) -> dict[str, Any]:
    return yaml.safe_load((path or CONFIG_PATH).read_text(encoding="utf-8")) or {}


def deck_config(deck: str, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = cfg or load_config()
    decks = cfg.get("decks") or {}
    if deck not in decks:
        raise KeyError(f"unknown deck {deck!r}; configured: {sorted(decks)}")
    return decks[deck]


# --- scoring --------------------------------------------------------------


def is_release(row: dict[str, Any]) -> bool:
    return (
        str(row.get("type") or "") == "release"
        or str(row.get("source_role") or "") == "release"
        or str(row.get("judge_category") or "") == RELEASE_CATEGORY
    )


def category_of(row: dict[str, Any]) -> str:
    if is_release(row):
        return RELEASE_CATEGORY
    return str(row.get("judge_category") or "").strip() or UNCATEGORIZED


def _signal(row: dict[str, Any], name: str, default: float) -> float:
    signals = row.get("judge_signals")
    if isinstance(signals, dict) and signals.get(name) is not None:
        try:
            return float(signals[name])
        except (TypeError, ValueError):
            pass
    return default


def score_priors(candidates: list[dict[str, Any]], cfg: dict[str, Any]) -> dict[str, float]:
    """Median judged score per source role (key ``*`` for the window)."""
    by_role: dict[str, list[float]] = defaultdict(list)
    for row in candidates:
        if is_release(row) or row.get("judge_score") is None:
            continue
        score = float(row["judge_score"])
        by_role[str(row.get("source_role") or "")].append(score)
        by_role["*"].append(score)
    priors = {role: statistics.median(values) for role, values in by_role.items() if values}
    priors.setdefault("*", float((cfg.get("unjudged") or {}).get("fallback", 0.35)))
    return priors


def base_score(row: dict[str, Any], cfg: dict[str, Any], priors: dict[str, float]) -> tuple[float, str]:
    """(score, basis) before the weighted signals."""
    if is_release(row):
        release_cfg = cfg.get("release") or {}
        tier = str(row.get("release_tier") or "unknown")
        return float(release_cfg.get(tier, release_cfg.get("unknown", 0.3))), f"release:{tier}"
    if row.get("judge_score") is not None:
        return float(row["judge_score"]), "judge"
    unjudged = cfg.get("unjudged") or {}
    role = str(row.get("source_role") or "")
    prior = priors.get(role, priors.get("*"))
    return float(unjudged.get("scale", 0.9)) * float(prior), f"prior:{role or '*'}"


def utility(row: dict[str, Any], cfg: dict[str, Any], priors: dict[str, float]) -> tuple[float, dict[str, float]]:
    weights = cfg.get("weights") or {}
    unjudged = cfg.get("unjudged") or {}
    score, basis = base_score(row, cfg, priors)
    judged = row.get("judge_score") is not None
    relevant = _signal(row, "platform_relevant", float(unjudged.get("platform_relevant", 0.5))) if judged else float(unjudged.get("platform_relevant", 0.5))
    marketing = _signal(row, "corporate_marketing", float(unjudged.get("corporate_marketing", 0.2))) if judged else float(unjudged.get("corporate_marketing", 0.2))
    sources = max(1, int(row.get("source_count") or 1))
    parts = {
        "score": round(float(weights.get("judge_keep", 1.0)) * score, 4),
        "platform_relevant": round(float(weights.get("platform_relevant", 0.0)) * relevant, 4),
        "coverage": round(float(weights.get("coverage", 0.0)) * math.log1p(sources - 1), 4),
        "source_tune": round(float(weights.get("source_tune", 0.0)) * float(row.get("source_tune") or 0.0), 4),
        "in_edition": round(float(weights.get("in_edition", 0.0)) * (1.0 if int(row.get("edition_runs") or 0) > 0 else 0.0), 4),
        "corporate_marketing": round(-float(weights.get("corporate_marketing", 0.0)) * marketing, 4),
    }
    total = round(sum(parts.values()), 4)
    parts["basis"] = basis  # type: ignore[assignment]
    return total, parts


# --- story collapse -------------------------------------------------------


def story_id(row: dict[str, Any]) -> str:
    key = str(row.get("story_key") or "").strip()
    return key if key else f"url:{row.get('key') or row.get('url')}"


_EDITORIAL = None


def _editorial():
    global _EDITORIAL
    if _EDITORIAL is None:
        try:
            try:
                import editorial
            except Exception:  # pragma: no cover
                from pipeline import editorial
            _EDITORIAL = (editorial, editorial.load_config())
        except Exception:
            _EDITORIAL = (None, {})
    return _EDITORIAL


def event_tokens(row: dict[str, Any]) -> set[str]:
    """``model|version`` anchors in the title, e.g. ``kimi|3.1``.

    The feed's cluster keys include the normalized headline, so two
    headlines about one launch ("Moonshot ... K3.1 Pro", "Kimi K3.1 Pro ...")
    stay separate across runs. A recap card is per event, so the deck merges
    stories that name the same model at the same version. A version is
    required: "claude" alone would merge a week of unrelated stories.
    """
    module, cfg = _editorial()
    if module is None:
        return set()
    try:
        features = module._features(row, cfg)
    except Exception:
        return set()
    version = features.get("version_family")
    if not version:
        return set()
    return {f"{model}|{version}" for model in features.get("models") or ()}


def group_stories(candidates: list[dict[str, Any]], merge_events: bool = True) -> dict[str, list[dict[str, Any]]]:
    """Group candidates by story key, then join groups sharing an event token."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for row in candidates:
        sid = story_id(row)
        find(sid)
        if merge_events:
            for token in event_tokens(row):
                union(sid, f"event:{token}")
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        groups[find(story_id(row))].append(row)
    return groups


def collapse_stories(candidates: list[dict[str, Any]], cfg: dict[str, Any], priors: dict[str, float]) -> list[dict[str, Any]]:
    merge_events = bool((cfg.get("collapse") or {}).get("merge_model_version_events", True))
    groups = group_stories(candidates, merge_events)
    stories = []
    for sid, members in groups.items():
        def rank(row: dict[str, Any]) -> tuple:
            return (
                base_score(row, cfg, priors)[0],
                int(row.get("edition_runs") or 0),
                str(row.get("published") or ""),
                str(row.get("key") or ""),
            )

        members = sorted(members, key=rank, reverse=True)
        rep = dict(members[0])
        sources = {str(m.get("source") or "") for m in members}
        sources.discard("")
        rep["source_count"] = max(int(rep.get("source_count") or 1), len(sources))
        rep["edition_runs"] = max(int(m.get("edition_runs") or 0) for m in members)
        rep["story_id"] = story_id(rep)
        rep["member_urls"] = [m.get("url") or m.get("key") for m in members]
        stories.append(rep)
    return stories


# --- selection ------------------------------------------------------------


def _category_bounds(deck: dict[str, Any], category: str) -> tuple[int, int]:
    cats = deck.get("categories") or {}
    default = cats.get("default") or {}
    spec = {**default, **(cats.get(category) or {})}
    lo = int(spec.get("min", 0) or 0)
    hi = spec.get("max")
    hi = int(deck.get("budget", 0)) if hi is None else int(hi)
    return lo, max(lo, hi)


def _role_cap(deck: dict[str, Any], role: str) -> int:
    spec = (deck.get("roles") or {}).get(role) or {}
    cap = spec.get("max")
    return int(deck.get("budget", 0)) if cap is None else int(cap)


def source_roles(stories: list[dict[str, Any]]) -> dict[str, str]:
    """One role per source (its most common non-empty role), so the role
    layer nests the source layer and the flow stays exact."""
    counts: dict[str, Counter] = defaultdict(Counter)
    for story in stories:
        role = str(story.get("source_role") or "")
        if role:
            counts[str(story.get("source") or "")][role] += 1
    return {source: c.most_common(1)[0][0] for source, c in counts.items()}


def _source_cap(deck: dict[str, Any], source: str) -> int:
    overrides = deck.get("source_overrides") or {}
    if source in overrides:
        return int(overrides[source])
    return int(deck.get("max_per_source", deck.get("budget", 0)))


def solve(stories: list[dict[str, Any]], deck: dict[str, Any], budget: int | None = None) -> list[str]:
    """Return the selected story ids. ``stories`` must carry ``utility``."""
    budget = int(deck.get("budget", 0) if budget is None else budget)
    min_utility = float(deck.get("min_utility", 0.0))
    eligible = [s for s in stories if float(s["utility"]) >= min_utility and float(s["utility"]) > 0]
    if budget <= 0 or not eligible:
        return []

    sources = sorted({str(s.get("source") or "") for s in eligible})
    role_of = source_roles(stories)
    roles = sorted({role_of.get(name, "") for name in sources})
    categories = sorted({category_of(s) for s in eligible})
    role_index = {name: 2 + i for i, name in enumerate(roles)}
    src_base = 2 + len(roles)
    src_index = {name: src_base + i for i, name in enumerate(sources)}
    item_base = src_base + len(sources)
    cat_base = item_base + len(eligible)
    cat_index = {name: cat_base + i for i, name in enumerate(categories)}
    source_node, sink = 0, 1
    mcf = MinCostFlow(cat_base + len(categories))

    for name, node in role_index.items():
        mcf.add_edge(source_node, node, _role_cap(deck, name), 0)
    for name, node in src_index.items():
        mcf.add_edge(role_index[role_of.get(name, "")], node, _source_cap(deck, name), 0)
    handles = []
    for i, story in enumerate(eligible):
        node = item_base + i
        cost = -int(round(float(story["utility"]) * SCALE))
        handles.append(mcf.add_edge(src_index[str(story.get("source") or "")], node, 1, cost))
        mcf.add_edge(node, cat_index[category_of(story)], 1, 0)
    for name, node in cat_index.items():
        lo, hi = _category_bounds(deck, name)
        if lo:
            mcf.add_edge(node, sink, lo, -FLOOR_BONUS)
        if hi - lo:
            mcf.add_edge(node, sink, hi - lo, 0)

    mcf.solve(source_node, sink, budget)
    return [eligible[i]["story_id"] for i, handle in enumerate(handles) if mcf.flow_on(handle) > 0]


def _bench_reason(story: dict[str, Any], deck: dict[str, Any], picked_by_source, picked_by_cat, n_picked: int, budget: int, picked_by_role=None, role_of=None) -> str:
    if float(story["utility"]) < float(deck.get("min_utility", 0.0)):
        return "below_min_utility"
    source = str(story.get("source") or "")
    if picked_by_source[source] >= _source_cap(deck, source):
        return f"source_cap:{source}"
    role = (role_of or {}).get(source, "")
    configured = role in (deck.get("roles") or {})
    if configured and picked_by_role is not None and picked_by_role[role] >= _role_cap(deck, role):
        return f"role_cap:{role or 'unknown'}"
    category = category_of(story)
    if picked_by_cat[category] >= _category_bounds(deck, category)[1]:
        return f"category_cap:{category}"
    if n_picked >= budget:
        return "budget"
    return "not_beneficial"


CARD_FIELDS = (
    "story_id",
    "key",
    "url",
    "title",
    "source",
    "source_role",
    "type",
    "published",
    "story_key",
    "judge_score",
    "judge_verdict",
    "judge_category",
    "release_tier",
    "source_count",
    "edition_runs",
    "best_edition_rank",
    "summary",
    "member_urls",
)


def _card(story: dict[str, Any]) -> dict[str, Any]:
    card = {field: story.get(field) for field in CARD_FIELDS if story.get(field) not in (None, "", [])}
    card["category"] = category_of(story)
    card["utility"] = story["utility"]
    card["utility_parts"] = story["utility_parts"]
    return card


def score_stories(candidates: list[dict[str, Any]], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    priors = score_priors(candidates, cfg)
    stories = collapse_stories(candidates, cfg, priors)
    for story in stories:
        story["utility"], story["utility_parts"] = utility(story, cfg, priors)
    stories.sort(key=lambda s: (-float(s["utility"]), str(s.get("story_id"))))
    return stories


def select(
    candidates: list[dict[str, Any]],
    deck_name: str,
    *,
    cfg: dict[str, Any] | None = None,
    budget: int | None = None,
) -> dict[str, Any]:
    cfg = cfg or load_config()
    deck = deck_config(deck_name, cfg)
    budget = int(deck.get("budget", 0) if budget is None else budget)
    stories = score_stories(candidates, cfg)
    chosen = set(solve(stories, deck, budget))

    shortlist = [s for s in stories if s["story_id"] in chosen]
    role_of = source_roles(stories)
    picked_by_source: dict[str, int] = defaultdict(int)
    picked_by_role: dict[str, int] = defaultdict(int)
    picked_by_cat: dict[str, int] = defaultdict(int)
    for story in shortlist:
        source = str(story.get("source") or "")
        picked_by_source[source] += 1
        picked_by_role[role_of.get(source, "")] += 1
        picked_by_cat[category_of(story)] += 1

    bench = []
    for story in stories:
        if story["story_id"] in chosen:
            continue
        if len(bench) >= int(deck.get("bench", 10)):
            break
        card = _card(story)
        card["bench_reason"] = _bench_reason(story, deck, picked_by_source, picked_by_cat, len(shortlist), budget, picked_by_role, role_of)
        bench.append(card)

    return {
        "deck": deck_name,
        "config_version": cfg.get("version"),
        "budget": budget,
        "min_utility": deck.get("min_utility"),
        "candidates": len(candidates),
        "stories": len(stories),
        "eligible": sum(1 for s in stories if float(s["utility"]) >= float(deck.get("min_utility", 0.0))),
        "shortlist": [_card(s) for s in shortlist],
        "bench": bench,
        "by_category": dict(sorted(picked_by_cat.items())),
        "by_role": dict(sorted(((r or "unknown"), n) for r, n in picked_by_role.items())),
        "by_source": dict(sorted(picked_by_source.items(), key=lambda kv: (-kv[1], kv[0]))),
    }


def build_selection(
    deck_name: str,
    start: Any,
    end: Any,
    *,
    types: set[str] | None = None,
    exclude_urls: set[str] | None = None,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Load the judged candidates for a window and select. Never raises.

    Used by the recap bundle builders behind ``--selector``. ``types``
    defaults to the deck's configured types.
    """
    try:
        try:
            import deck_candidates
        except Exception:  # pragma: no cover
            from pipeline import deck_candidates
        cfg = cfg or load_config()
        deck = deck_config(deck_name, cfg)
        types = types if types is not None else (set(deck.get("types") or []) or None)
        candidates, diag = deck_candidates.load_candidates(start, end, types=types, exclude_urls=exclude_urls)
        out = select(candidates, deck_name, cfg=cfg)
        out["window"] = [str(start), str(end)]
        out["candidate_diag"] = diag
        return out
    except Exception as exc:
        return {"deck": deck_name, "error": str(exc), "shortlist": [], "bench": []}
