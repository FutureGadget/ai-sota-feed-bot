---
title: "Leto scores memory by whether it improves the next answer, not fidelity to the past"
date: 2026-11-25
theme: recall-and-curation
evidence: [9f9cac7b2636dce8]
---
Leto treats memory as prediction: it keeps conversation details reachable through an index, then *replays* memory on each request to supply context the request does not state. A utility loop uses response outcomes to refine future selection. Against six memory systems on five benchmarks, it beats the strongest by **16.3 points** on PrefEval accuracy and **3.1** on PERMA task completion, and leads MemoryArena with gains that grow with chain depth. On long-context tasks it matches retrieval over raw history while serving fewer tokens.

For builders: a faithful memory store can still serve useless context. Measure memory by its effect on downstream answers, and feed that signal back into what gets served.
