---
title: "Revolut cut AI coding token spend to about a tenth by self-hosting GLM at $0.30 per million tokens"
date: 2026-11-16
theme: cheaper-models
evidence: [62499695b24c28e4]
---
Revolut's AI operations lead said on the AI Engineer podcast that self-hosted GLM models run at a **blended $0.30 per million tokens**, about **one-tenth** of its previous Anthropic and OpenAI coding spend. Data covers roughly **2,000 engineers over a year** (company-reported, via a secondary write-up).

The lever was constraint: fewer GPUs than the load suggests, less context than the models advertise, lower precision, and narrower agent permissions. Earlier, Claude Code at scale had engineers spending $1,000-10,000 a month with little measured impact at first.

For builders: at fleet scale, a self-hosted open-weight model with capped context and quantization can beat per-seat frontier spend. Measure lead time before and after, as Revolut did.
