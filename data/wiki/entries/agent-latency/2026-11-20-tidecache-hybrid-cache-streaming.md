---
title: "TideCache streams hybrid-model attention caches layer by layer and completes up to 2.04x more agent turns"
date: 2026-11-20
theme: kv-state
evidence: [024d4dfaa92472bb]
also: [agent-cost]
---
Hybrid open-weight models keep two cache types: global-attention KV that grows with context, and bounded recurrent state. TideCache, built on SGLang for GB300 and GH200 superchips, manages both. It **prefetches the next global-attention layer's prefix into shared GPU slots** while bounded-state layers compute, so long prefixes need not stay resident in HBM. A scheduler picks resident or streamed execution per request.

Against SGLang with HiCache across seven model/platform setups, the authors report up to **2.04x more agent turns**, 20-59% lower P50 per-token latency, and 1.40-3.05x faster agent P50 TTFT. For builders serving hybrid models: cache management written for pure-attention models leaves capacity unused, and the gain depends on CPU-GPU superchip bandwidth.
