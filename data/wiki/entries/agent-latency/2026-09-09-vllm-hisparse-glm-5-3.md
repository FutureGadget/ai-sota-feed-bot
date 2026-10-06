---
title: "vLLM's HiSparse tier keeps GLM 5.3 decoding when its KV cache no longer fits in GPU memory"
date: 2026-09-09
theme: kv-state
evidence: [be33ba45a7db1738]
---
vLLM integrates **HiSparse as a pressure-driven memory tier** that composes with the Hybrid Memory Allocator and KV offloading. It activates once a request's KV state no longer fits in GPU memory, so GLM 5.3 requests keep decoding instead of stalling or falling back to a slower path.

Concurrency stays high exactly where the storage-bandwidth bottleneck would otherwise cap it.
