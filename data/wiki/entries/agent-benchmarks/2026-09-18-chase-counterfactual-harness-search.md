---
title: "CHASE flags harness gains that come from benchmark shortcuts instead of capability"
date: 2026-09-18
theme: trusting-the-score
evidence: [38522ce275c55bf2]
---
Automatic harness optimization can produce a **"cheating harness"** whose gain on a released benchmark depends on a benchmark-wide shortcut. Counterfactual Harness Search and Evolution (CHASE) searches for protocol changes that would destroy a claimed gain while preserving task semantics, keeping a validity firewall and an archive of confirmed counterfactuals.

On OfficeQA it retains most genuine gains while substantially reducing gains a counterfactual protocol change would erase. The benchmark itself starts resisting harness gaming.
