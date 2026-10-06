---
title: "vllm-metal brings paged KV cache and packed batching to Apple Silicon for concurrent agent load"
date: 2026-09-23
theme: concurrent-serving
evidence: [6a60d1242802c6f9]
---
vllm-metal brings vLLM's scheduler, paged KV cache, and continuous batching to Apple Silicon (M1 Pro through M5 Pro). It replaces padded batching with **packed queries**, concatenating request tokens into one ragged batch instead of padding each request to the same length. The release also adds batched MTP and automatic M5 prefill acceleration, and reports flatter TTFT under concurrent agent load.

Padding overhead grows with every request sharing a batch, so this is a concurrency fix, not a raw-speed one. Paged block tables let variable-length sequences share memory without reshaping the cache, which is what makes admission control workable under concurrent load.
