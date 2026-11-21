---
title: "e-RWSC stops Best-of-N sampling once an answer's majority is certified at a chosen error rate"
date: 2026-11-21
theme: consistency-and-autonomy
evidence: [dcba5842407a5f4a]
also: [agent-cost]
---
Best-of-N spends the same sampling budget on every prompt, and adaptive early-stopping uses tuned thresholds with no error guarantee. e-RWSC groups candidates by final answer, weights them by reward score, and runs a **betting e-process per answer**. It halts only when one answer is certified to hold a majority, with the chance of certifying a wrong answer bounded by a chosen **alpha** at every point in time.

The paper shows Wald's sequential test loses this guarantee because the leading answer shifts mid-run. Reported accuracy beats baselines at **substantially lower token cost**. For builders: self-consistency loops can carry an explicit error budget instead of a hand-tuned sample count.
