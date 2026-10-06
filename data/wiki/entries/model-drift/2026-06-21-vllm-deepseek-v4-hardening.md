---
title: "vLLM 0.23 reworks DeepSeek-V4 serving across backends"
date: 2026-06-21
theme: serving-runtime-drift
evidence: [435cc52d2f08f897]
---
vLLM v0.23.0 (408 commits from 200 contributors) gives DeepSeek-V4 another **hardening and optimization pass**: sparse MLA metadata decoupled from V3.2, a TRTLLM-gen attention kernel, EPLB for the Mega-MoE, and selective prefix-cache retention for sliding-window KV cache.

Changes like these can move latency, throughput, and sampling behavior with no model swap. A serving-runtime upgrade belongs behind the same regression gate.
