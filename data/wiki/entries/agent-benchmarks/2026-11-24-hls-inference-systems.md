---
title: "Coding agents given 36 hours and 8xH200s to build inference servers: one model beat baseline in 71% of runs"
date: 2026-11-24
theme: long-horizon-and-subsystems
evidence: [d83b1979c150d8ae]
---
*Humanity's Last System* gives agents live GPU sandboxes with up to **8xH200** and up to **36 hours** to build a serving system specialized to a model, hardware, and production workload. A token-level verifier checks output against a trusted reference while allowing normal numerical variation; a server that fails verification scores zero. Opus 5 beat the baseline in **71%** of runs; no other agent passed **24%**. The authors released 150+ trajectories with **238,000+** steps.

For builders: on ultra-long tasks the spread between frontier models is far wider than on short coding suites, so a short benchmark is a poor proxy for multi-day agent work.
