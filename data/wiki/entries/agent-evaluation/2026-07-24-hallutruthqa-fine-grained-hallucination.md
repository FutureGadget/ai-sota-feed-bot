---
title: "HalluTruthQA: detecting a hallucination is easier than locating and explaining it"
date: 2026-07-24
theme: domain-benchmarks
evidence: [1b0f607e0ee0acbd]
---
**HalluTruthQA** is a 2,400-example Arabic QA benchmark across four domains (Islamic knowledge, history, science, geography) with verified references, six candidate answers, character-level error spans, human explanations, and macro/micro hallucination types.

Zero-shot across Allam, Falcon-H1, Qwen32, and Silma, no model wins every sub-task. Best scores: **0.880** Macro-F1 on detection, but only **0.516** F1 on span localization, 0.852 on factual verification, 0.644 on explanation. Catching *that* an answer is wrong is easier than showing *where* and *why*.
