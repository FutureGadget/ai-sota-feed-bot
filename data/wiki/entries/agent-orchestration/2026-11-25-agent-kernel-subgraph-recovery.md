---
title: "Agent-Kernel re-runs only a failed node's descendants: 100% recovery vs 55% for whole-trajectory replay"
date: 2026-11-25
theme: runtime-substrate
evidence: [11920e09b3795c97]
also: [agent-reliability]
---
Agent-Kernel ports subgraph-selective recovery from Spark and Erlang/OTP to the LLM content plane. On a raw exception, **Sub-Graph Recovery** resets the failed node's descendants, keeps completed siblings, and passes each parent's text into its children's prompts, on a durable substrate with a formal state-preservation guarantee. No trained verifier or planner is involved. Across **14,434** runs on tau-bench, Gaia2, AutomationBench, and InterruptBench, it fully recovered within a budget of 3 where full replay reached **55%**, about **10x** faster than an adapted Sherlock rollback. Removing it dropped success to **39.4%**; parallel structure gave up to **12.7x** speedup.

For builders: treat a run as a task graph and retry the failed subtree, not the whole trajectory.
