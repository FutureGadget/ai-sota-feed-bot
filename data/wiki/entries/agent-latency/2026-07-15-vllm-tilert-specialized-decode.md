---
title: "vLLM and TileRT pair stock prefill with a specialized decode engine over RDMA"
date: 2026-07-15
theme: engine-architecture
evidence: [d08095949d6300c2]
---
TileRT plugs a **decode-only runtime** into vLLM's prefill/decode split through the V1 connector interface, with zero changes to vLLM. KV state moves from stock vLLM prefill nodes to TileRT decode nodes over RDMA, and multi-token speculative decoding starts as soon as it lands.

It reaches peak decode throughput at a best-case 4.0-token acceptance rate on an 8-GPU setup. Today it is limited to **one in-flight request per decode node** and a narrow model list.
