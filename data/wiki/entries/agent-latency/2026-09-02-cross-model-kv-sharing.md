---
title: "A cross-model KV layer lets one model skip prefill that another model already paid for"
date: 2026-09-02
theme: kv-state
evidence: [da31200faa97b5f9]
---
A universal context-reuse layer translates the KV state one model produced into a form a **different model** can consume, skipping the second model's prefill.

- Same family (Qwen2.5-7B to 1.5B): LongBench2 accuracy *rises* from 27.59% to 34.48%.
- Across families (Qwen2.5-1.5B to Gemma-2-2B): up to **67.05% less prefill cost** at 4K context.
- Large to small (Llama3.1-70B to Qwen2.5-7B): end-to-end latency drops **from 899ms to 138ms**, at 44.0% vs 45.7% accuracy.

It fits multi-model pipelines where a cheap model would otherwise redo a bigger model's prefill.
