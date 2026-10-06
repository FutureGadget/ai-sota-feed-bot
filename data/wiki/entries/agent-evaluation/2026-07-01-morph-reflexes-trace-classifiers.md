---
title: "Multi-head classifiers score many behavioral failures in one pass over a trace"
date: 2026-07-01
theme: grading-trajectories
evidence: [cf0a37dd32efaf51]
---
Morph Reflexes serves behavioral signals from agent traces — **looping, reasoning leakage, user frustration** — from a small model with multiple classifier heads over one forward pass, built on a vLLM-derived inference engine, at sub-30ms latency.

The pitch is explicit: judging every turn with a frontier model is too slow and expensive at scale. Per-signal heads make "watch every trace for every failure mode" an inference-cost question rather than N judge calls.
