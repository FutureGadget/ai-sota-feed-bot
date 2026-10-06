---
title: "TALRanker decides per document when reranking should call a search tool"
date: 2026-07-14
theme: better-retrievers
evidence: [12c546b2fc140ca1]
also: [vector-kb]
---
The Tool-Adaptive LLM Reranker (TALRanker) targets hallucinated relevance judgments on queries beyond the model's own knowledge. Calling a search tool for every document during reranking fixes accuracy but adds prohibitive latency, so TALRanker **frames pointwise relevance scoring as an agentic decision process** that invokes external tools only where needed.

It adds a middle option to the rerank stage between a purely parametric reranker and a tool call per candidate.
