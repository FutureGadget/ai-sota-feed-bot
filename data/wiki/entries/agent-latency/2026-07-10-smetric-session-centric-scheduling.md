---
title: "SMetric schedules agent sessions to balance load without losing KV-cache reuse"
date: 2026-07-10
theme: agent-traffic
evidence: [07f37058d3d7c72b]
---
SMetric finds agent traffic already has **over 80% KV-cache reuse** in production, but generic schedulers over-index on cache locality and let load imbalance cap cluster throughput. Agents act only on complete responses, so cluster tokens per second matters more than per-token latency.

It load-balances the first hop of each agent session, then routes every later request cache-aware. Reported gains versus prior schedulers: **10-16% throughput** under prefill-decode colocation and 2-34% on prefill under disaggregated serving.
