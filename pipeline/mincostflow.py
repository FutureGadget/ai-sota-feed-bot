"""Small exact min-cost flow solver (successive shortest paths).

Dijkstra with Johnson potentials. Initial potentials come from Bellman-Ford,
so negative edge costs are allowed as long as the input graph has no negative
cycle (true for the layered selection graph in ``deck_select``).

``solve`` augments one shortest path at a time and stops at ``max_flow`` or
when the next path would not lower the total cost (``stop_at_nonnegative``).
Successive-shortest-path costs are non-decreasing, so stopping there gives the
minimum-cost flow over every flow value up to ``max_flow``.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field

INF = float("inf")


@dataclass
class Edge:
    to: int
    rev: int
    cap: int
    cost: int
    flow: int = 0


@dataclass
class MinCostFlow:
    n: int
    graph: list[list[Edge]] = field(init=False)

    def __post_init__(self) -> None:
        self.graph = [[] for _ in range(self.n)]

    def add_edge(self, u: int, v: int, cap: int, cost: int) -> tuple[int, int]:
        """Add u->v. Returns a handle (u, index) for reading the flow later."""
        self.graph[u].append(Edge(v, len(self.graph[v]), cap, cost))
        self.graph[v].append(Edge(u, len(self.graph[u]) - 1, 0, -cost))
        return u, len(self.graph[u]) - 1

    def flow_on(self, handle: tuple[int, int]) -> int:
        u, index = handle
        return self.graph[u][index].flow

    def _bellman_ford(self, source: int) -> list[float]:
        dist = [INF] * self.n
        dist[source] = 0
        for _ in range(self.n - 1):
            changed = False
            for u in range(self.n):
                if dist[u] == INF:
                    continue
                for e in self.graph[u]:
                    if e.cap - e.flow > 0 and dist[u] + e.cost < dist[e.to]:
                        dist[e.to] = dist[u] + e.cost
                        changed = True
            if not changed:
                break
        return dist

    def solve(self, source: int, sink: int, max_flow: int, stop_at_nonnegative: bool = True) -> tuple[int, int]:
        """Return (flow, cost)."""
        potential = [0 if d == INF else d for d in self._bellman_ford(source)]
        total_flow = 0
        total_cost = 0
        while total_flow < max_flow:
            dist = [INF] * self.n
            prev: list[tuple[int, int] | None] = [None] * self.n
            dist[source] = 0
            heap = [(0.0, source)]
            while heap:
                d, u = heapq.heappop(heap)
                if d > dist[u]:
                    continue
                for i, e in enumerate(self.graph[u]):
                    if e.cap - e.flow <= 0:
                        continue
                    nd = d + e.cost + potential[u] - potential[e.to]
                    if nd < dist[e.to]:
                        dist[e.to] = nd
                        prev[e.to] = (u, i)
                        heapq.heappush(heap, (nd, e.to))
            if dist[sink] == INF:
                break
            path_cost = dist[sink] - potential[source] + potential[sink]
            if stop_at_nonnegative and path_cost >= 0:
                break
            for v in range(self.n):
                if dist[v] < INF:
                    potential[v] += dist[v]
            push = max_flow - total_flow
            v = sink
            while v != source:
                u, i = prev[v]  # type: ignore[misc]
                e = self.graph[u][i]
                push = min(push, e.cap - e.flow)
                v = u
            v = sink
            while v != source:
                u, i = prev[v]  # type: ignore[misc]
                e = self.graph[u][i]
                e.flow += push
                self.graph[v][e.rev].flow -= push
                v = u
            total_flow += push
            total_cost += push * int(path_cost)
        return total_flow, total_cost
