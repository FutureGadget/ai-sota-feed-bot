---
title: "Vector search alone falls short; fuse BM25 and vector results with Reciprocal Rank Fusion"
date: 2026-06-18
theme: hybrid-and-graph
evidence: [425a66a9c84b30ae]
---
An InfoQ practitioner article describes the limits of RAG pipelines built on vector search alone, and an internal omni-search application that combines **BM25 lexical results and vector results with Reciprocal Rank Fusion (RRF)**.

Hybrid dense-plus-lexical retrieval, usually followed by a rerank pass, is the production floor. Pure top-k similarity misses exact terms, IDs, and names that keyword search catches.
