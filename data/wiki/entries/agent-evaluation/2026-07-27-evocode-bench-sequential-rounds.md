---
title: "Over 227 sequential rounds, regressions, not missing features, limit coding agents"
date: 2026-07-27
theme: coding-benchmarks
evidence: [f94c501f001ba6a5]
---
**EvoCode-Bench** tests coding agents across **227 sequential rounds** in a persistent workspace instead of one bounded task. Single-turn scores overstate reliability: the bottleneck is **regressions accumulating** across rounds, not missing features.

Long-lived agent workflows need regression checks between steps, not only a final pass.
