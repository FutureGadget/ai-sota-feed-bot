---
title: "Anthropic's hillclimbing guide sets four checks for an eval and a held-out split"
date: 2026-09-29
theme: gaming-and-containment
evidence: [5f38f7da2d8e299d]
---
Anthropic's guide to eval design and hillclimbing (the `claude-api` skill's `build-eval` and `hillclimb` commands) sets four checks for a usable eval: tasks mirror production, stronger models and higher effort score better, the top model sits **well below 100%**, and run-to-run variance is low. A task that fails every replicate is treated as ambiguous, not hard.

To keep hillclimbing honest it splits cases into a train set the optimizer may read and a **test set it never sees**, forbids pasting failure transcripts into prompts, and suggests cost reduction at score parity for saturated evals.
