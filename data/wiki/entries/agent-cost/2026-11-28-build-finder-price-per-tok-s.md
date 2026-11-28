---
title: "A roofline-style model prices self-hosted decode speed per build and publishes its error"
date: 2026-11-28
theme: caching-and-serving
evidence: [b35fcbcf3ef6343e]
also: [agent-latency]
---
Build Finder ranks hardware builds for a chosen open-weight model by **price per token per second** of decode. Its catalog covers 273 GPUs, 619 CPUs, and 333 systems at dated US street prices. Each operation takes the longer of reading its bytes or doing its arithmetic, fitted to 424 one-session benchmarks. A two-parameter correction for concurrent sessions is fitted to 418 measured runs.

The error is published. The median estimate is **11% low** on NVIDIA, but **1.43x** too high on Macs. On an RTX 3090 the fit never saw, 87% of runs land within 1.25x. Speculative decoding, which the model ignores, measured **2.3x** the estimate.

For builders: size self-hosted inference at your real session count. Treat Mac estimates as optimistic.
