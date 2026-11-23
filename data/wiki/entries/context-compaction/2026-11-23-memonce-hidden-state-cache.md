---
title: "MemOnce caches final-layer hidden states and decodes them into KV, shrinking long-context state 1,313x"
date: 2026-11-23
theme: compressed-serving
evidence: [d43ec4840a23ed16]
also: [agent-memory]
---
MemOnce is an architecture change, not a prompt technique: it stores compact final-layer hidden states as memory and decodes them back into KV caches when needed. For Qwen3.5-4B at 1M-token context, the authors report a **1,313x** smaller memory-state cache and **6.9x** lower prefill latency.

For builders: this needs a model trained for it, so it is not a drop-in serving flag. It signals where long-agent-session cost may go: compressed state the model itself can expand, rather than external summarization.
