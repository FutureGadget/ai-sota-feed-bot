---
title: "Cost-optimized models act on poisoned business data far more often than frontier models"
date: 2026-07-23
theme: adversarial-and-security
evidence: [44f0a4a9788e78b0]
---
ActionRail's benchmark tests whether an agent executes **corrupted-but-plausible business data**, such as an altered payment account or a fake refund address, buried in an otherwise legitimate document.

Across 8 models from 4 providers on 10 consequential workflows, **cost-optimized models failed 48.3-63.3%** of the time versus 1.7-21.7% for frontier models. A guard layer blocked all 480 protected attack cases with zero false positives. This failure mode needs a dedicated defense, not just a stronger model. The guard layer and results are ActionRail's own.
