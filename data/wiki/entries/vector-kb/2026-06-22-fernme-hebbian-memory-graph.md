---
title: "FERNme builds a memory graph from co-occurrence with near-zero LLM calls"
date: 2026-06-22
theme: beyond-vectors
evidence: [eb5267262e7d31c8]
---
FERNme grows an agent memory graph using **fuzzy edges and a Hebbian co-occurrence rule** to create memory tags. The structure comes from what appears together, not from embeddings, and updates take roughly zero LLM calls.

Keeping the LLM out of the *write* path as well as the read path removes the per-turn token cost most memory layers pay to extract facts. It is a hobby-scale project, so treat it as a design idea, not a benchmark.
