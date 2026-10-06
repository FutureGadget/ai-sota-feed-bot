---
title: "vLLM Decode Context Parallelism shards the KV cache for 3x long-context throughput"
date: 2026-08-09
theme: kv-state
evidence: [fcb5eeae253e1eba]
---
vLLM's **Decode Context Parallelism (DCP)** shards the KV cache across GPUs along the sequence dimension. It reports **3x higher throughput** on long-context agentic workloads versus standard tensor parallelism.

It attacks the storage-bandwidth bottleneck through parallelism rather than compression or offload: each GPU holds and reads only its slice of a long agent context.
