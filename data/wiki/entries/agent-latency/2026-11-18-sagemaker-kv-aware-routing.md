---
title: "SageMaker routes each request to the replica that actually holds its cached prefix"
date: 2026-11-18
theme: kv-state
evidence: [ef90af83544e1ea4]
---
SageMaker AI real-time endpoints added **KV-aware routing**. vLLM containers publish a cache event on every store and evict. A managed index keeps truncated hashes of cached content per instance, and the router sends each request to the instance with the longest token match that isn't too busy.

It fixes two failures of the earlier hash-the-first-N-bytes prefix routing. That router kept sending requests to instances that had already evicted the cache. It also scattered early chat turns while they were shorter than the configured prefix length. For multi-turn agents this keeps a growing history on one warm replica. It needs at least two instances, falls back to load-aware routing, and is enabled with one environment variable plus `RoutingStrategy: KV_AWARE`.
