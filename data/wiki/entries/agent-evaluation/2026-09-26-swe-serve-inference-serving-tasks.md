---
title: "SWE-Serve: 53 SGLang engineering tasks, 20.8-75.5% pass rates across configs"
date: 2026-09-26
theme: coding-benchmarks
evidence: [485a8d96b72d9981]
---
NVIDIA's **SWE-Serve** turns real SGLang engineering work — model integration, public APIs, cache systems, GPU kernels — into **53 tasks** qualified against reference solutions and regression tests. It scores Pass@1 across 31 model/harness configurations (three runs each) with public web access blocked.

Pass rates range **20.8-75.5%**. For teams running their own serving stack, it is the closest public proxy for agent work on inference code; see [agent latency](/topic/agent-latency).
