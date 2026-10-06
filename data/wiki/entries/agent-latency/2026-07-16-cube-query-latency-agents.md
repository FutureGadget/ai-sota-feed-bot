---
title: "One agent request fans out into dozens of queries, each held to a chat-era latency budget"
date: 2026-07-16
theme: beyond-the-engine
evidence: [3f7129b93f7a9b75]
---
Cube argues that a single agent request fans out into tens of database or API queries, and a multi-step workflow into hundreds. Each inherits chat-era expectations: **a few hundred milliseconds feels responsive, a couple of seconds feels broken**.

The dashboard semantic-layer pattern (pre-aggregated rollups served through query rewriting, columnar storage with partition pruning) is being repurposed as agent infrastructure because it was built for many small interactive queries, not a few large batch ones.
