---
title: "Generating one case at calibrated ambiguity exposes a cliff a pass rate hides"
date: 2026-07-10
theme: score-validity
evidence: [37ded4dcb25847bf]
---
Discovery Bench, covered in Google Cloud's "Who evaluates the evaluations?", uses **surprisal** — the uncertainty a query leaves about the correct answer — to generate the same case at controlled ambiguity levels instead of hand-labeling "easy" and "hard".

- On the identical query, agent, and ground truth, F1 fell from **1.00 at neutral phrasing to 0.00** at high ambiguity.
- Mid-ambiguity cases sometimes beat low-ambiguity ones, exposing quirks such as over-retrieval of time-sharded tables.
- The audit found benchmark ground truth wrong on **6.49% of MMLU**.

The eval data needs evaluating too.
