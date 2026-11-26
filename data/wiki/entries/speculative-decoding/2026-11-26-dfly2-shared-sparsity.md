---
title: "DFly2 drafts from the target's own KV cache and sparse index picks for long-context speculative decoding"
date: 2026-11-26
theme: draft-methods
evidence: [bb4c90dec13b8ea7]
also: [agent-latency]
---
Long contexts make a drafter's separate KV cache expensive. DFly2 is a block-parallel drafter that keeps no cache of its own: it reuses the target model's KV cache and the target's per-query sparse attention selections. The authors report it accepts more tokens per step than the DFlash and DSpark drafters.

For builders: on long agent contexts, drafter memory competes with the target for KV space. A drafter that shares the target's cache and sparsity removes that cost, which matters most when serving many long sessions per GPU.
