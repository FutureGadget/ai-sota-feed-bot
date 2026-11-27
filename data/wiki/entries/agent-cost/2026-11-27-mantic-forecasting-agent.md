---
title: "An RL-tuned small forecasting agent matches a frontier model at 1/15 the cost per forecast"
date: 2026-11-27
theme: cheaper-models
evidence: [94438c04413384cb]
---
Mantic post-trained Inkling 2 Small with RL on Tinker. The reward mixes the realized outcome's log score with a frontier-ensemble reference forecast to cut single-question noise. On 200 held-out numerical questions, the agent roughly matches Fable 5.2 (medium) at about **1/15 the cost** per forecast (vendor-reported). The bottleneck was tooling, not the model: third-party APIs were too slow for thousands of concurrent rollouts, so Mantic ingested point-in-time data, including a 1.32 TB Wikipedia snapshot, into its own stores.

For builders: a narrow, high-volume agent job is where fine-tuning a small model pays off. Budget for rollout-grade tool backends; rate-limited APIs cannot serve RL training.
