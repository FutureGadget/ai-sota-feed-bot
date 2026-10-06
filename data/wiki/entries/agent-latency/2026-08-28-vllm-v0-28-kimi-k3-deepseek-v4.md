---
title: "vLLM v0.28.0 speeds up Kimi K3 and lands DeepSeek V4 sparse MLA for every decode mode"
date: 2026-08-28
theme: day-0-support
evidence: [99ece13e787f3487]
---
vLLM v0.28.0 continues the **Kimi K3** optimization stack-wide: Decode Context Parallel support, fused FlashKDA decode and prefill kernels, combined all-gathers with a 1.5-3x kernel-level speedup, an adaptive speculative token budget for **about 60% better DSpark time-to-first-token**, and shared-expert sharding that saves about 17 GiB per GPU.

It also lands DeepSeek V4's sparse MLA end-to-end across plain decode, MTP, and DSpark speculative decoding. The fast path now covers every decode mode the model runs.
