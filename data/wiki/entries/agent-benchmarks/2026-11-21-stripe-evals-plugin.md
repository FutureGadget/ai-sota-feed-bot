---
title: "Stripe evals: a vendor agent plugin raised integration scores on all 14 model-harness pairs"
date: 2026-11-21
theme: domain-suites
evidence: [0fd95d308fe40417]
---
Stripe ran **69 roleplay-driven scenarios** (hosted checkout, metered billing, per-seat subscriptions, marketplace splits) across **14 model and harness pairs**, with and without its own agent plugin. Agents without it drift to older APIs common in pretraining data, miss features, and hallucinate parameters; existing coding benchmarks miss this because they check that code passes, not that the integration is current. Stripe reports that **all 14 agents scored higher with the plugin** (vendor-reported).

For builders: if your platform exposes an API to coding agents, grade generated integrations against your current recommended patterns, and ship the guidance as a plugin or skill rather than hoping the model's training data is recent.
