---
title: "Most agent optimizers stop helping once applied repeatedly on Terminal-Bench 2.0"
date: 2026-07-16
theme: score-validity
evidence: [8605a4348aa09d77]
---
A continual-learning evaluation on **Terminal-Bench 2.0** applies optimization recursively as new tasks arrive. GEPA's optimized agent transferred below baseline on new tasks; Meta Harness improved once but not with a second budget. Only regression-controlled RELAI-VCL held the top pass rate at every stage:

- RELAI-VCL: **76.4%** lifelong average
- GEPA: 66.0%
- Meta Harness: 64.6%
- Baseline: 58.7%

One-shot gains on a fixed benchmark say little about a deployed agent tuned over time.
