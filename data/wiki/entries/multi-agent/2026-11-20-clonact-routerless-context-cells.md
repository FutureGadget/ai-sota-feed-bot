---
title: "Routerless context virtualization doubles true-conflict merge success with 45.9% fewer prompt tokens"
date: 2026-11-20
theme: shared-context
evidence: [6a67d6fc89489d89]
also: [context-compaction]
---
An always-on personal agent juggling many streams in one session suffers *constraint bleed* between topics and head-of-line stalls. Router-and-ticket hierarchies instead pay for lossy prose handoffs and blind merges, landing true-conflict repository merges at **33.3%**. ClonAct swaps the router for isolated context cells, a non-generative context manager, and a trial merge gate that tests a merge before committing it.

The trial merge gate alone lifts true-conflict merges to 63.3%. ClonAct reaches the same rate with 45.9% fewer prompt tokens and 95.0% completion under surge load. For builders: isolate contexts and test merges, rather than routing work through a coordinator that rewrites it as prose.
