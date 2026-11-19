---
title: "AgentDojo scored 433 runs as failed attacks even though the agent took the attacker's decisive action"
date: 2026-11-19
theme: adversarial-and-security
evidence: [cd759e6684ea23fc]
also: [prompt-injection]
---
An audit checked AgentDojo's automated attack verdicts against the tool calls agents actually made, then re-ran its attacks on **24 current models** from eight developers under protocols published before the runs. On the 19,381 published runs, benchmark and audit agree on **97.7%** of runs that did not crash. But the benchmark marked **433 runs** as "no attack" in which the agent executed the attacker's decisive action, such as paying the attacker.

For builders: a security benchmark's pass rate is an output of its success check, not ground truth. Before ranking models on injection resistance, audit a sample of verdicts against the raw tool-call trace.
