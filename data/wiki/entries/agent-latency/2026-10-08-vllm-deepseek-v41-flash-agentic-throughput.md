---
title: "vLLM lifts DeepSeek-V4.1-Flash agentic throughput 5x within three weeks of release"
date: 2026-10-08
theme: day-0-support
evidence: [611a6830e42643a9]
---
vLLM reports that, three weeks after DeepSeek-V4.1-Flash shipped, it made the model **1.9x faster at low concurrency** and raised throughput **5x on SemiAnalysis AgentX**, an agentic benchmark (vendor-reported). The gains come from SWA bounded replay, CUDA graphs, DeepSeek's new kernels, and vLLM's own kernel fusions.

For builders: day-0 support is the start of the serving curve, not the end. Re-benchmark a self-hosted model a few weeks after launch before sizing capacity from launch-week numbers.
