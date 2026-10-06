---
title: "Awareness Local hits 96.0% recall@5 on LongMemEval with no LLM in retrieval"
date: 2026-08-30
theme: local-first-stores
evidence: [5f608b2d21b1899e]
---
**Awareness Local** stores memories as git-compatible Markdown, indexes them with SQLite FTS5 plus optional local embeddings, and retrieves with hybrid BM25-plus-vector reciprocal rank fusion, with no LLM in the loop. It reports **96.0% recall@5 on LongMemEval**.

That is in the same range Sibyl reported on the same benchmark. Hybrid retrieval without an LLM is becoming a repeatable recipe, not one team's result.
