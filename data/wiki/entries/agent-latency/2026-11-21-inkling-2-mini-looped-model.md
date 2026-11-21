---
title: "vLLM serves Inkling 2 Mini on day 0, a looped model that runs its middle layers three times per token"
date: 2026-11-21
theme: day-0-support
evidence: [227c0cb62bf0dc78, 824c03b970f1dc58]
---
Thinking Machines' Inkling 2 Mini runs its **middle 12 layers three times per token** with shared weights, each pass with its **own KV cache** and gated messages from the pass before. It is a multimodal MoE with **26B total and 3.5B active** parameters, up to 1M tokens of context, and a native DSpark speculator. vLLM supports it on Blackwell, Hopper, and DGX Spark on launch day, and Hugging Face pitches it for local setups.

For builders: a looped model's active-parameter count understates its per-token cache footprint, since each loop pass keeps separate KV state, so size memory from the serving engine's numbers, not the parameter count.
