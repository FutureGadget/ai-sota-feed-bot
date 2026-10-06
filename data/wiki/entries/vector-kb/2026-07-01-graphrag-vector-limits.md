---
title: "Vector RAG falls short on global context, multi-hop reasoning, and provenance"
date: 2026-07-01
theme: hybrid-and-graph
evidence: [567c0f7008740f1a]
---
Cassie Shum's InfoQ talk on GraphRAG names three gaps where traditional vector retrieval structurally fails: **global context, multi-hop reasoning, and provenance**. The proposed fix is a semantically structured knowledge graph that pushes orchestration logic down into the data layer.

The graph-vs-vector choice is about what similarity search cannot answer, not taste. If your questions span documents or need a traceable source, plan for structure in the data, not more prompt logic on top.
