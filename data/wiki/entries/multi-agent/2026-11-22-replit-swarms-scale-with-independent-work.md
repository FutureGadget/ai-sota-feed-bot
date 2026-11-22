---
title: "32-agent swarms cut NumPy runtime 18.9x vs 3.7x solo, but gains track how independent the work is"
date: 2026-11-22
theme: when-it-pays
evidence: [1475b63ec37aeffc]
also: [agent-benchmarks]
---
Replit's Optimization-Bench gives agents two hours to speed up pinned open-source libraries, scored on a separate VM with hidden inputs and an out-of-process timer. On NumPy's 13 independent workloads, one Opus 5.5 agent reached **3.7x** and a 32-agent swarm **18.9x**. On Git, where all 7 workloads share 15 files, swarms barely beat a solo agent. GPT-6.2 Astra was the strongest solo agent, yet its swarms got worse as they grew.

Unprompted, the best swarms sent few direct messages and claimed tasks on a shared board. Weak swarms routed everything through a coordinator whose inbox grew with each agent. The comparison holds wall-clock fixed, not compute: a swarm spends up to 32x the tokens. For builders: add agents only when the work splits into independent pieces.
