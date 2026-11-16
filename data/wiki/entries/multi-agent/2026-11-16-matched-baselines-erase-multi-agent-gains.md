---
title: "Against compute-matched baselines, multi-agent setups average -4.2 points and lose 74% of contrasts"
date: 2026-11-16
theme: when-it-pays
evidence: [6abf544ebe49a8ae]
---
A meta-analysis of nine studies and 516 multi-agent configurations argues most comparisons are confounded: they pit a communicating system against **one greedy pass**, mixing coordination with extra samples and extra compute.

Against baselines matched on sample count or resource budget, multi-agent systems averaged **-0.042 accuracy**, and equalled or trailed the baseline in **74%** of contrasts. Switching from a greedy to a sampled baseline alone moved the difference by -0.038 (paper-reported).

The authors' mechanism: agents that share identical evidence gain nothing by talking. Positive returns need **partitioned evidence, an external verifier, or error diversity across models**.

For builders: before adding agents, benchmark against best-of-N on the same budget. Split agents only where they see different data.
