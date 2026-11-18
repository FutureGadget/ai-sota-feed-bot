---
title: "Fusing a decoder layer into two kernel launches roughly doubles single-user decode speed in vLLM on AMD"
date: 2026-11-18
theme: engine-architecture
evidence: [70c82430c7b2a8f8]
---
At low concurrency, a coding agent waits on decode, and decode is a chain of small GPU kernels, each paying launch and drain costs. vLLM's FlyDSL **MonoKernels** run several dependent stages inside one persistent launch, prefetching later weights and handing off tiles as soon as they are ready.

On MI325X, one decoder layer went from **32 kernels in 320 µs to 2 kernels in 115 µs**. Single-user P90 interactivity rose from 182 to 411 tok/s on agentic-session traces. The gains are largest at concurrency 1 and shrink as batch grows. For DeepSeek-V4.1-Flash at concurrency 4, two TP4 replicas beat one mono TP8 server by 26%. It is opt-in (`--monokernel`) and ships per model, so check that your model is covered.
