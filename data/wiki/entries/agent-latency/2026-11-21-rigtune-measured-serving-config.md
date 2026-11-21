---
title: "Measured serving-config search beat expert vLLM settings by 1.5-2.3x, with a different winner per model"
date: 2026-11-21
theme: engine-architecture
evidence: [1c77760f5ff21c14]
also: [speculative-decoding]
---
rigtune benchmarks engines (vLLM, SGLang, llama.cpp), weight precisions, KV-cache types, and speculative decoding on your GPU with your prompts, then serves the winner behind an OpenAI-compatible API. The author reports **at least 1.8x** over stock and vLLM `auto_tune` on Qwen3.5-9B, **1.5-1.7x** over the best expert setting on Gemma 4 12B, and **2.26x** over stock vLLM for Qwen3.5-35B-A3B on an H200, with GSM8K answers holding up.

The winning trick differed each time: the checkpoint's own MTP head (off by default), suffix decoding, or fp8 weights plus fp8 KV cache. For builders: serving flags don't transfer across models or GPUs, so measure on your workload.
