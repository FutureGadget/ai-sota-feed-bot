---
title: "Pruning redundant rounds from training trajectories cuts inference tokens ~48%"
date: 2026-09-18
theme: harness-and-context
evidence: [1a4323f628b5253c]
---
Dependency-Aware Trajectory Refinement treats a multi-turn agent trajectory as a **round-level dependency DAG**, finds which rounds (failed tool calls, parallel sub-queries, verification-only steps) the final answer depends on, and fine-tunes on the pruned trajectories.

Across four multimodal QA benchmarks it improves accuracy by **up to 1.7 points** over vanilla fine-tuning while cutting per-sample inference messages **~40%** and inference tokens **~48%**. Redundant training data inflates the same per-step bill as redundant context, so the fix can sit upstream of compaction.
