---
title: "Disaggregated serving of Qwen3.8-2.4T reaches 5K tokens/sec on GB300 NVL72, with a reproducible recipe"
date: 2026-09-23
theme: engine-architecture
evidence: [c30b19170c960cb5]
---
vLLM's prefill/decode-disaggregated serving of **Qwen3.8-2.4T** on GB300 NVL72 reaches **5,000 tokens/sec aggregate throughput** and 180 tokens/sec per-user interactivity. The write-up publishes the methodology so other teams can reproduce the result on their own stack.

A reproducible recipe turns a launch-day number into a baseline you can test your own deployment against.
