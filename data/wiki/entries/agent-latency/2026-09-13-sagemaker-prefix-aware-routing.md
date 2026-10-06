---
title: "SageMaker prefix-aware routing cuts P50 TTFT up to 77% by keeping KV caches warm"
date: 2026-09-13
theme: kv-state
evidence: [4f4661ca3038bcff]
---
Amazon SageMaker Inference's **prefix-aware routing** sends requests that share a prompt prefix to the same instance, so the KV cache an earlier request built is still warm. On Llama 3.1 70B it cut **P50 time-to-first-token by up to 77%** and raised the KV cache hit rate from about 25% to over 80%.

No cache repair is needed, only co-location. Once a service fans out across many instances, request placement matters as much as cache compression.
