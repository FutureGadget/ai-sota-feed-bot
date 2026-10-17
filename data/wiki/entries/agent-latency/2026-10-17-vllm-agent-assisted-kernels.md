---
title: "vLLM ships agent-written decode kernels, gated by scoped changes and correctness tests"
date: 2026-10-17
theme: engine-architecture
evidence: [58d2e800a62db5e1, 5726df15bb134984]
---
Two vLLM posts describe agent-assisted optimization of decode paths. The Kimi K3 post covers CuTe DSL kernels for decode on NVIDIA GB300; the Reflection Beam-1.0 post (501B total, 23B active) reports **2.71x lower decode latency** (vendor-reported) alongside DFlash2 speculative decoding with adaptive verification.

The Kimi K3 post stresses the guardrails: scoped changes, correctness tests, and reproducible benchmarks before an agent-written kernel ships.

For builders: treat kernel speedups from agents like any other perf patch. Ask for the correctness suite and a reproducible benchmark before adopting the engine release.
