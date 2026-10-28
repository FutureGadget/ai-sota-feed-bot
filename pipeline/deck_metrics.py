"""Selection metrics for the editor decks.

A deck is a fixed-budget selection, so precision and recall move together
and F1 hides the trade-off. These metrics score a ranked list of story ids
against owner grades (0 drop, 1 useful, 2 must-read):

- ``must_cover_recall``: share of must-include stories in the list (the
  recall guard).
- ``alpha_ndcg``: graded nDCG with a redundancy discount. A story's gain is
  multiplied by ``(1 - alpha)`` for every earlier pick in the same duplicate
  group, so two cards about one event count less than two events. The ideal
  list is built greedily, as is standard for alpha-nDCG.
- ``graded_sum``: total grade of the list (the set-level utility).
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Iterable


def must_cover_recall(selected: Iterable[str], must: set[str], k: int | None = None) -> float | None:
    if not must:
        return None
    chosen = list(selected)[: k if k is not None else None]
    return round(len(set(chosen) & must) / len(must), 4)


def _discount(position: int) -> float:
    return 1.0 / math.log2(position + 2)


def _dcg(ranked: list[str], grades: dict[str, float], groups: dict[str, str], alpha: float) -> float:
    seen: dict[str, int] = defaultdict(int)
    total = 0.0
    for position, sid in enumerate(ranked):
        grade = float(grades.get(sid) or 0.0)
        group = groups.get(sid, sid)
        total += grade * (1.0 - alpha) ** seen[group] * _discount(position)
        seen[group] += 1
    return total


def ideal_ranking(grades: dict[str, float], groups: dict[str, str], alpha: float, k: int) -> list[str]:
    remaining = {sid for sid, grade in grades.items() if grade and grade > 0}
    seen: dict[str, int] = defaultdict(int)
    ranked: list[str] = []
    while remaining and len(ranked) < k:
        best = max(
            sorted(remaining),
            key=lambda sid: float(grades[sid]) * (1.0 - alpha) ** seen[groups.get(sid, sid)],
        )
        ranked.append(best)
        seen[groups.get(best, best)] += 1
        remaining.discard(best)
    return ranked


def alpha_ndcg(
    ranked: Iterable[str],
    grades: dict[str, float],
    groups: dict[str, str] | None = None,
    *,
    alpha: float = 0.5,
    k: int | None = None,
) -> float | None:
    ranked = list(ranked)
    k = len(ranked) if k is None else k
    ranked = ranked[:k]
    groups = groups or {}
    ideal = _dcg(ideal_ranking(grades, groups, alpha, k), grades, groups, alpha)
    if ideal <= 0:
        return None
    return round(_dcg(ranked, grades, groups, alpha) / ideal, 4)


def graded_sum(selected: Iterable[str], grades: dict[str, float]) -> float:
    return round(sum(float(grades.get(sid) or 0.0) for sid in selected), 4)


def duplicate_groups(same_as: dict[str, str | None]) -> dict[str, str]:
    """Resolve ``same_as`` links (story -> another story) into group ids."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for sid, other in same_as.items():
        find(sid)
        if other:
            a, b = find(sid), find(str(other))
            if a != b:
                parent[max(a, b)] = min(a, b)
    return {sid: find(sid) for sid in parent}
