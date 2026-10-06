---
title: "vLLM Decode Context Parallelism triples long-context decode throughput"
date: 2026-08-09
theme: caching-and-serving
evidence: [fcb5eeae253e1eba]
---
vLLM's **Decode Context Parallelism** shards the KV cache across GPUs by sequence dimension instead of offloading it, reporting **3x higher throughput** on long-context agentic workloads versus standard tensor parallelism.

More throughput per GPU-hour on the same hardware is a direct cost lever, not only a latency one. See [agent latency](/topic/agent-latency) for the serving detail.
