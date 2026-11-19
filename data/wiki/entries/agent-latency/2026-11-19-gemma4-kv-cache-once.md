---
title: "Storing Gemma 4's tied key/value cache once cuts decode KV memory 1.34-1.40x with unchanged kernels"
date: 2026-11-19
theme: kv-state
evidence: [a2babe4c488b1701]
---
In Gemma 4 31B's global attention layers, the key is a fixed scaling of the value, yet the open engines the authors checked still store a full key and a full value (1,024 values per KV head and token). Storing one **640-value row** and reading it through two overlapping strided views lets a stock paged-attention kernel run unchanged.

In a vLLM prototype, steady decode KV memory per request falls **1.34-1.40x** at 32K-64K tokens, and a decode engine with a fixed 15 GiB pool ran **1.38x** the decode tokens per step on 16K prompts. Costs: an eager step is 4-9% slower at equal batch, and it does not yet stack with an 8-bit KV cache. For builders: model-specific cache layouts are free capacity that engines leave on the table.
