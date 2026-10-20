---
title: "Audit an LLM judge for stability, chance-corrected human agreement, and ensemble divergence"
date: 2026-10-20
theme: trusting-the-judge
evidence: [4e6e796fa0c5bfc0]
---
A Google Cloud consulting post lists the judge biases to test for: verbosity, position, halo, agreeableness, and self-enhancement. It cites swapped option order flipping verdicts over 75% of the time and judges missing up to 75% of bad outputs (figures as cited by the vendor, no methodology given).

Its audit has three steps:
- **Stability:** score the same output several times and measure variance; high variance means the rubric is ambiguous.
- **Human alignment:** use chance-corrected agreement, because a lenient judge looks good on mostly valid data.
- **Ensembles:** one judge per criterion, and at least two models on the same output to flag divergence.

For builders: report chance-corrected agreement, not raw accuracy, before trusting a judge in CI.
