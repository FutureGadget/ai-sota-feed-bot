---
title: "vLLM benchmarks five draft methods on AMD GPUs; the best method varies by model and task"
date: 2026-08-28
theme: draft-methods
evidence: [b4fa4d7778a6247d]
---
vLLM's guide to speculative decoding on AMD Instinct GPUs compares native MTP, Gemma 4's paired MTP checkpoint, EAGLE-3, parallel-draft DFlash, and DSpark (DFlash plus a Markov head). The winner changes by model and benchmark:

- Gemma-4-26B: **2.87x** on MATH500 with DFlash, 2.74x on GSM8K with Gemma 4 MTP
- Qwen3.5-122B: 2.20x on MATH500 with native MTP
- Kimi-K2.5: 2.68x on MATH500 with DFlash; Qwen3-8B: 1.63x on GSM8K with DSpark

Tune `num_speculative_tokens` per workload (DFlash typically peaks near N=7). Watch mean accepted length and per-position acceptance rate, not only end-to-end throughput, to catch a pairing that costs more than it saves.
