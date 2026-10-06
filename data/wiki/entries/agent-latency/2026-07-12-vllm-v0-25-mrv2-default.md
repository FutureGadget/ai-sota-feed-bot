---
title: "vLLM v0.25.0 makes Model Runner V2 the default and removes PagedAttention"
date: 2026-07-12
theme: engine-architecture
evidence: [76c7b104c7dfd8b4]
---
vLLM v0.25.0 makes **Model Runner V2 the default execution path for all dense models** and deletes the legacy PagedAttention implementation. MRv2 gains prefix caching for Mamba hybrid models and dynamic speculative decoding compatible with full CUDA graphs. Tool-call and reasoning-token parsing across model families is unified under one Streaming Parser Engine.

Teams pinned to older vLLM releases should plan the upgrade: the attention path the engine was first known for is gone.
