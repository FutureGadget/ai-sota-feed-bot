---
title: "The inference backend alone explains about 39% of benchmark score variance"
date: 2026-08-11
theme: serving-runtime-drift
evidence: [2db97c49b795a2d1]
---
A fully crossed study (three instruction-tuned models × five inference frameworks such as HuggingFace, vLLM, and Ollama × six benchmarks × four generation modes) finds that **the serving backend explains roughly 39% of the score variance** a practitioner sees out of the box, even under deterministic decoding.

Framework name and version belong next to the model ID as variables you pin and disclose. See [agent evaluation](/topic/agent-evaluation).
