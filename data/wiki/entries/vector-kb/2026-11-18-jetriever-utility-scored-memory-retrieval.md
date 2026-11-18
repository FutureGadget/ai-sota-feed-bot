---
title: "Scoring every memory for usefulness, not similarity, put the right one first in 85% of indirect queries"
date: 2026-11-18
theme: beyond-vectors
evidence: [b5bf234c229cd676]
also: [agent-memory]
---
**Jetriever** drops similarity search for agent memory. It asks a decision model (Jev) to score every stored memory for usefulness to the current question. On InMind's 125 indirect-query tasks, where the useful memory doesn't resemble the question, it ranked the gold exchange first in **84.8%** of cases. Matched BM25 and MiniLM controls managed 1.6% and 0%. On 60 MemoryAgentBench questions it scored 55.4% against 44.3% for ReFind.

The cost is a model call over the whole pool: about **$0.008 per InMind question** and $0.031 per MemoryAgentBench question. That is cheap for a small personal store and grows linearly with pool size, so for large stores it works as a reranker behind a cheap first-stage filter.
