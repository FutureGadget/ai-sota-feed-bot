---
title: "One judge error correction reused across agents can reorder rankings; audited AIPW keeps bias under 0.003"
date: 2026-11-24
theme: correcting-judge-error
evidence: [65021a141fd5a47d]
also: [agent-evaluation]
---
*Transport-Safe Evaluation of LLM Agents* shows that measuring a judge's error rate once and applying it to every agent fails when the judge's errors depend on the trajectory. On a four-agent semi-synthetic benchmark, a scalar correction with oracle calibration reached maximum bias **0.245** and never recovered the true ranking in **250** replications. Augmented inverse-probability weighting with a random human audit kept maximum bias below **0.003** with about **95%** coverage.

For builders: if agents fail in different ways, a single judge accuracy number does not transfer between them. Keep a small random human audit per agent and combine it with judge scores, instead of correcting with one global error rate.
