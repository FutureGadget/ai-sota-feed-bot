---
title: "IMABO tunes model choice and retrieval depth online as a bandit on live traffic"
date: 2026-09-07
theme: routing
evidence: [0b14d37d00fa2210]
---
"Bandits in Prod" notes that agents often can only judge a configuration (model selection, retrieval depth, prompting strategy, temperature) by **running it on live requests and reading noisy feedback**, with no representative validation set. It casts this as online hyperparameter optimization, an infinitely many-armed bandit, and introduces **IMABO**; its IMOSS policy grows the active set of candidate configurations over time.

The authors evaluate it on classical ML tuning and LLM agent configuration. It automates the per-request choice a team would otherwise hand-write and forget to revisit.
