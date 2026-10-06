---
title: "vLLM Semantic Router runs a bounded micro-agent inside the serving layer"
date: 2026-07-03
theme: agent-traffic
evidence: [c0c3ec4a6aba7980]
---
vLLM Semantic Router turns its `vllm-sr/auto` routing into a bounded **micro-agent runtime**: confidence scoring, ratings, model fusion, and workflows run *inside* the serving layer instead of in a separate orchestration hop above it.

Each orchestration hop removed is a full model call's latency the agent no longer pays. The serving layer is starting to absorb logic that used to live in the application.
