---
title: "Following handoff records locates the failing step in multi-agent traces with up to 97.6% fewer tokens"
date: 2026-11-13
theme: diagnosis
evidence: [ae75fdfb8dec6766]
also: [multi-agent]
---
Multi-agent traces interleave steps from different agents and repeat content across messages, so a model asked to find the decisive error has to read long, cluttered records.

CoLFA uses the collaboration structure the run already recorded. Handoff-guided step expansion picks which steps to examine by following how executions connect. Cross-referenced content organization presents passed-along content once instead of at every hop.

Across five settings on Who&When and LongRCA with three backbone models, it reports the highest exact step-localization accuracy at the lowest token use: up to 37.5% better accuracy and up to 97.6% fewer tokens than individual baselines. Both figures are best cases. Paper-reported.

For trace tooling: capture handoff edges explicitly, because they make automated root-cause analysis cheaper.
