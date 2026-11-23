---
title: "An advocate-skeptic-arbitrator debate with a belief-change stopping rule used 2.4x fewer LLM calls"
date: 2026-11-23
theme: when-it-pays
evidence: [b953eb7d1f6cfc42]
also: [agent-cost]
---
A research-verification framework assigns asymmetric roles (Advocate, Skeptic, Arbitrator) instead of one model critiquing itself, and stops the debate when the arbitrator's belief stops moving (a Belief-Delta rule) rather than after a fixed number of rounds. Across 200 runs on 40 hypotheses with DeepSeek-R1-32B, it reports **2.4x** fewer LLM calls.

For builders: much multi-agent cost is rounds that change nothing. A convergence-based stop is cheap to add to any debate or review loop.
