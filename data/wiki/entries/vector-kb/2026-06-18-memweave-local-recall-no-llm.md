---
title: "A local memory store reaches 98% Recall@5 on LongMemEval-S with no LLM in the recall path"
date: 2026-06-18
theme: recall-quality
evidence: [2d698f04404f697d]
---
memweave, an open-source local agent memory, reports **98% Recall@5 on LongMemEval-S** without calling an LLM or needing an API key.

High recall on a standard memory benchmark is reachable with retrieval engineering alone. Model scale is not the bottleneck, and the recall path can stay local, cheap, and deterministic.
