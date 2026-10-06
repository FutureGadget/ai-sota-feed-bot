---
title: "RaBitQCache compresses the KV cache with rotated binary quantization"
date: 2026-07-01
theme: kv-state
evidence: [0933879c19d86a9c]
---
RaBitQCache uses **randomized rotated binary quantization** to compress the KV cache, and an adaptive top-p token budget instead of a fixed top-k for sparse-attention retrieval, holding generation quality on long-context inference.

It cuts the memory I/O that DualPath names as the agentic bottleneck: a smaller cache is less state to move at every step.
