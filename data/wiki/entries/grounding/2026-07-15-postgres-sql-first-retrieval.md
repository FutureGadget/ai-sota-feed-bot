---
title: "Postgres for agents: assemble context with plain SQL first, vectors only for the fuzzy slice"
date: 2026-07-15
theme: retrieval-architecture
evidence: [1609e44adca88f23]
---
Gwen Shapira's InfoQ talk shows teams delivering **deterministic and semantic context** from one Postgres: JSONB and plain SQL for what can be looked up exactly ("how would a human solve this?"), HNSW vector indexing for genuinely fuzzy matches, and **vector quantization for roughly 4x faster queries**.

Deterministic retrieval is a live alternative to embedding everything. Reach for similarity search only when an exact query cannot express the question.
