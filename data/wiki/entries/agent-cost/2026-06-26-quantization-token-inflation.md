---
title: "Quantized reasoning models emit more tokens, eating their per-token discount"
date: 2026-06-26
theme: cheaper-models
evidence: [c4fa725d5c123b2d]
also: [proving-agent-roi]
---
"Quantization Inflates Reasoning" shows that low-bit post-training quantization, the standard way to cut inference cost, makes reasoning models **emit more tokens to reach the same answer**. Final-answer accuracy and per-token latency both miss this hidden test-time cost.

The bill that matters is price per token times tokens spent. Every downshift (smaller model, quantized model, cheaper judge) has to be costed on **total tokens emitted in the loop**, not the sticker price.
