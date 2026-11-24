---
title: "Pipelined top-p sparse attention in vLLM sped up block selection 1.17-1.80x and fit up to 8x larger batches"
date: 2026-11-24
theme: less-work-per-step
evidence: [25b4eea501a6e6c1]
---
*DisSparse* integrates top-p sparse attention into vLLM for long-context serving. A two-stream pipeline overlaps block selection with attention, and a histogram-based kernel cuts selection cost. The authors report **1.17-1.80x** faster block selection and up to **8x** larger batches.

For builders: long agent contexts make attention, not weights, the bottleneck. Top-p selection adapts how many KV blocks each step reads, which matters for agent traffic whose context grows with every tool result.
