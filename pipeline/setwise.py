"""Setwise comparison scoring: rank small groups, fit Bradley-Terry scores.

A pointwise judge scores each story alone, and its scores bunch near the top
(Jev keeps most on-topic items near 0.9). Ranking a small group of stories
against each other gives an ordering signal instead. This module holds the
pure parts; ``scripts/setwise_eval.py`` asks the model and compares the
result with owner grades.

- ``make_groups``: deterministic groups of ``size`` where every item appears
  ``rounds`` times, shuffled differently each round.
- ``pairs_from_ranking``: a ranked group becomes winner/loser pairs.
- ``bradley_terry``: Bradley-Terry strengths by the MM algorithm (Hunter
  2004), with a small prior win against a virtual opponent so an item that
  never loses stays finite.
- ``auc``: probability that a random positive outranks a random negative.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from typing import Hashable, Iterable, Sequence


def make_groups(ids: Sequence[Hashable], size: int = 8, rounds: int = 4, seed: int = 0) -> list[list[Hashable]]:
    ids = list(ids)
    if len(ids) <= size:
        return [ids] if len(ids) >= 2 else []
    rng = random.Random(seed)
    groups: list[list[Hashable]] = []
    n_groups = math.ceil(len(ids) / size)
    for _ in range(rounds):
        order = ids[:]
        rng.shuffle(order)
        # Spread the remainder so no group is a lonely pair.
        groups.extend(order[i::n_groups] for i in range(n_groups))
    return [g for g in groups if len(g) >= 2]


def pairs_from_ranking(ranking: Sequence[Hashable]) -> list[tuple[Hashable, Hashable]]:
    return [(ranking[i], ranking[j]) for i in range(len(ranking)) for j in range(i + 1, len(ranking))]


def bradley_terry(
    items: Iterable[Hashable],
    pairs: Iterable[tuple[Hashable, Hashable]],
    prior: float = 0.5,
    iterations: int = 200,
) -> dict[Hashable, float]:
    """Log-strengths, centred at 0. Higher means preferred more often."""
    items = list(items)
    wins: dict[Hashable, float] = defaultdict(float)
    games: dict[Hashable, dict[Hashable, float]] = defaultdict(lambda: defaultdict(float))
    for winner, loser in pairs:
        wins[winner] += 1
        games[winner][loser] += 1
        games[loser][winner] += 1
    strength = {i: 1.0 for i in items}
    for _ in range(iterations):
        updated = {}
        for i in items:
            # The virtual opponent has strength 1 and splits `prior` games.
            denom = sum(n / (strength[i] + strength[j]) for j, n in games[i].items())
            denom += 2 * prior / (strength[i] + 1.0)
            updated[i] = (wins[i] + prior) / denom
        strength = updated
    logs = {i: math.log(s) for i, s in strength.items()}
    mean = sum(logs.values()) / len(logs) if logs else 0.0
    return {i: v - mean for i, v in logs.items()}


def auc(scores: dict[Hashable, float], positive: set[Hashable], negative: set[Hashable]) -> float | None:
    pos = [scores[i] for i in positive if i in scores]
    neg = [scores[i] for i in negative if i in scores]
    if not pos or not neg:
        return None
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))
