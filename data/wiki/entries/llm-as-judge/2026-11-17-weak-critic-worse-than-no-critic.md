---
title: "A naive 8B critic steered AutoML search below the no-critic random-search floor"
date: 2026-11-17
theme: trusting-the-judge
evidence: [ea00e78d97a3c87d]
---
A four-arm audit isolated what an LLM critic adds to an iterative search loop. A naive **8B** critic drove search below the random-search baseline on **7 of 8** tabular datasets, losing up to **0.245 AUC**. Stronger critics shrank the loss on this suite.

Fault injection explained why: errors with no consistent direction cost almost nothing under best-so-far search, but **directional** errors use up the finite search budget. A simple validation gate and a learned detector reduced the loss, but neither guaranteed matching the no-critic baseline.

For builders: a critic or judge in a refinement loop is not free. Run it against a no-critic arm before trusting it, and gate its feedback when it cannot be verified.
