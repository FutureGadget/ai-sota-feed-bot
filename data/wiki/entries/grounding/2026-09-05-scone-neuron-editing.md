---
title: "SCoNE makes RAG less distractible by strengthening context-aware neurons, with no fine-tuning"
date: 2026-09-05
theme: context-budget
evidence: [4be01fb545d6c7c4]
---
When retrieved documents mix useful and irrelevant context, models get distracted and hallucinate. **SCoNE** is a training-free edit: it finds context-aware FFN neurons with high attribution and high cross-input variability, then strengthens only those.

It needs a small mining sample, **no fine-tuning, and no inference-time overhead**, and reports consistent gains over baseline RAG methods on several knowledge-intensive QA benchmarks and two backbones. It applies to self-hosted open-weight models only.
