---
title: "Embedding charts as structured JSON beats larger multimodal embedders on chart-heavy retrieval"
date: 2026-08-28
theme: better-retrievers
evidence: [149a211377f80efa]
---
Databricks parses chart figures into **structured JSON with `ai_parse_document`** and embeds that enriched chunk instead of the caption alone, using a 300M-parameter embedding model. On chart-heavy **ViDoRe V3 (310 questions) it reaches 75.9% answer correctness** from the top-3 retrieved images, and 75.1% on a synthetic Chart-RAG set.

It beats four larger multimodal embedding baselines while passing the agent fewer images: a small model over structured content can out-retrieve a bigger one over raw pixels.
