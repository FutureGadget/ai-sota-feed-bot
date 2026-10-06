---
title: "TIGRAG builds a retrieval graph from token co-occurrence instead of LLM extraction"
date: 2026-07-01
theme: hybrid-and-graph
evidence: [c54c0758c14bd2c6]
---
TIGRAG constructs its knowledge graph from **token co-occurrence statistics** (a sliding-window count over the corpus) rather than an LLM extraction pipeline, then pairs the graph with neural reranking for multi-hop retrieval.

It reports matching or beating dense and LLM-extracted GraphRAG on multi-hop QA while cutting indexing time, inference latency, and prompt size. That weakens the standard objection that graph construction is too slow and costly for production.
