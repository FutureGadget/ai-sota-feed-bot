---
title: "Brex runs the same agent workflow code on Temporal in production and in-process for evals"
date: 2026-08-12
theme: eval-in-production
evidence: [a2351bb6d35107c3]
---
Brex writes workflow logic as pure business functions against a `Steps` interface and swaps the runtime underneath: **Temporal Cloud** in production, an in-process runtime for evals in Braintrust, Laminar, or LangSmith. The same orchestration code ships and gets evaluated.

The Temporal runtime took long-running onboarding-agent completion from roughly **96% to 99.9%**, and the pattern drives automated decisions on more than half of Brex's onboarding applications. Durability and fast eval iteration stop trading off once the runtime is a pluggable adapter.
