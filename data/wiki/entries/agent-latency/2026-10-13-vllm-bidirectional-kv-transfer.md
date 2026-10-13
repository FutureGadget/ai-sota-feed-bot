---
title: "vLLM bi-directional KV transfer lets prefill nodes reuse decode-side KV on later turns"
date: 2026-10-13
theme: kv-state
evidence: [bfe6eaadf6028df8]
---
In a disaggregated vLLM deployment, the decode node already holds the KV cache for tokens it generated. The vLLM blog describes sending that KV back to the prefill node so later turns of a conversation skip recomputing it, cutting time to first token by **up to 3.3x on long multi-turn prompts** (vendor-reported).

For builders: multi-turn agent traffic re-sends a growing history every turn, so prefill recompute dominates TTFT. If you run disaggregated serving, check whether your engine reuses decode-side KV before adding prefill capacity.
