---
title: "The inference backend alone explains about 39% of benchmark score variance"
date: 2026-08-11
theme: score-validity
evidence: [2db97c49b795a2d1]
---
A fully crossed study (three instruction-tuned models × five inference frameworks including HuggingFace, vLLM, and Ollama × six benchmarks) finds the **serving backend alone explains roughly 39%** of out-of-the-box score variance under deterministic, sampling-free decoding. The effect is strongest on factual benchmarks.

Framework names and versions are almost never disclosed. A benchmark report without backend, version, and generation config is not comparable to another, even for the same model and task.
