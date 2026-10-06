---
title: "vLLM's HPC-Ops backend tunes attention and FP8 MoE kernels for Hunyuan Hy3 on H20"
date: 2026-07-06
theme: engine-architecture
evidence: [7b0c24a5e0c92a10]
---
Tencent's HPC-Ops integrates Hopper-optimized attention and **FP8 MoE backends** into vLLM for the Hunyuan Hy3 model on NVIDIA H20, improving mixed-length decode, MoE latency, time-to-first-token, and time-per-output-token.

Serving gains are increasingly model- and hardware-specific. The mixed-length, bursty decode it targets is the pattern agent loops produce, not the uniform batches a generic benchmark assumes.
