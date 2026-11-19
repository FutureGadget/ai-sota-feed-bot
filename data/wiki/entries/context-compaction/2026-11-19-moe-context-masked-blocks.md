---
title: "MoE-Context masks unneeded context blocks in one KV cache; showing only the needed one lifts 93 to 119 of 120"
date: 2026-11-19
theme: curating-the-working-set
evidence: [e823044e69bd7a71]
---
MoE-Context splits context into blocks. Before each step, a fast yes/no pass decides which blocks the step needs; the rest stay as one-line notes and are **masked in a single KV cache** rather than deleted, so they can return without re-prefill.

On a laptop with Qwen3-1.7B and a synthetic lookup task, showing only the needed block raised accuracy from **93 to 119 of 120**. The weak link is selection: a probe lifted the model's own picking from 80 to 110 of 120 but did not transfer to a second task, and plain keyword search picked perfectly. For builders: masking makes curation reversible and cheap, but the selector still needs task-specific validation.
