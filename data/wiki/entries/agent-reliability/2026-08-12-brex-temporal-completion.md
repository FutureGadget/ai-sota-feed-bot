---
title: "Brex moved onboarding agents to Temporal and long-run completion rose from ~96% to 99.9%"
date: 2026-08-12
theme: execution-and-identity
evidence: [a2351bb6d35107c3]
---
Brex routes production onboarding-agent workflows through **Temporal Cloud** instead of a bespoke retry loop. Long-running completion rose from roughly **96% to 99.9%**, and the workflow code stayed unchanged because the durable runtime is swapped in underneath it.

Checkpoint recovery and exactly-once execution become infrastructure you buy, not logic you re-implement per agent. The same article covers running that code in-process for evals; see [agent evaluation](/topic/agent-evaluation).
