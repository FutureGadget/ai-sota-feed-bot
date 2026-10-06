---
title: "vLLM v0.26.0 ships a full Inkling stack and trims DeepSeek-V4 decode latency"
date: 2026-07-26
theme: day-0-support
evidence: [b811cc97eff4aae9]
---
vLLM v0.26.0 ships the **Inkling model family** with piecewise CUDA graphs, Hopper FA4 relative attention, MTP=1 speculative decoding, LoRA, and NVFP4 quantization in one release.

A DeepSeek-V4 performance push adds a specialized routing kernel (**2.94% end-to-end TPOT**), fused top-k bias (1.5-2x at kernel level), and redundant-copy removal (1.8% TPOT) without touching the serving architecture. Small per-step gains like these compound across every step of an agent loop.
