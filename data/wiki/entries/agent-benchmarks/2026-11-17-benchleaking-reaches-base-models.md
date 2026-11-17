---
title: "Benchmark test sets now leak into base models: ERNIE-5.5-Flash-Base reproduces 96% of HumanEval"
date: 2026-11-17
theme: trusting-the-score
evidence: [af4a65aeddbb525a]
---
Few-shot continuation on 20 benchmarks across four public base models found some models writing out complete test questions with answers that were not in their input. ERNIE-5.5-Flash-Base leaked **96%** of HumanEval problems with reference solutions and **85%** of OpenBookQA with answers, against 9% and none for DeepSeek-V4-Flash-Base.

The proposed **Anti-Hack score** recomputes a benchmark with every leaked item marked wrong. It cost DeepSeek-V4-Flash-Base 1.5 points, MiMo-V2.5-Base 5.0, and ERNIE-5.5-Flash-Base **16.6**. Post-training audits also show an agent stating hidden test requirements in 23% of attempts.

For builders: a public score on an open base model is not evidence of capability until it comes with a decontamination report. Fine-tunes inherit the leak.
