---
title: "On a local 7B model, two-call self-refinement beats a five-agent pipeline"
date: 2026-07-30
theme: when-it-pays
evidence: [b714943cd397084b]
---
A study ran Parishad, a five-role multi-agent pipeline, on **Qwen2.5-7B-Instruct** against direct prompting and two-call self-refinement on GSM8K and HumanEval. With JSON handoffs, the pipeline **dropped GSM8K accuracy from 75.0% to 45.0%** through error accumulation across roles, and two calls beat five agents.

The coordination tax is not just frontier-model economics hiding overhead. On small local models it shows up as lost accuracy, and the handoff format is part of the problem.
