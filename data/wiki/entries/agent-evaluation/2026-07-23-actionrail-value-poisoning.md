---
title: "Value-poisoning benchmark: cost-optimized models act on corrupted business data 48-63% of the time"
date: 2026-07-23
theme: domain-benchmarks
evidence: [44f0a4a9788e78b0]
---
ActionRail's **value-poisoning** suite tests whether an agent acts on corrupted-but-plausible business data — an altered payment account, a fake refund address — inside an otherwise legitimate document. Across 8 models from 4 providers on 10 consequential workflows:

- Cost-optimized models failed **48.3-63.3%** of the time; frontier models 1.7-21.7%.
- A guard layer blocked all **480** protected attack cases with zero false positives on legitimate ones.

This failure mode needs a dedicated defense, not just a stronger model.
