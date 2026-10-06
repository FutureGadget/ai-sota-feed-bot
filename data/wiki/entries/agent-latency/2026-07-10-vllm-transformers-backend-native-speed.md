---
title: "vLLM's transformers backend matches native throughput without per-model code"
date: 2026-07-10
theme: engine-architecture
evidence: [3ce97f6a8c6c0f29]
---
vLLM's transformers modeling backend uses `torch.fx` graph analysis plus AST rewriting to **fuse operations into optimized vLLM kernels automatically**. It matches native per-model integration throughput on dense and MoE Qwen3 models without hand-written per-model code.

Keeping up with new architectures is a maintenance tax on latency. This lowers the cost of getting a new model onto a fast path.
