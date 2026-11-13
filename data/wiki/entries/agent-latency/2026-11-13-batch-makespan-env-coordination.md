---
title: "Scheduling inference and environments together cut agent batch completion time by 10-65%"
date: 2026-11-13
theme: agent-traffic
evidence: [e372c76cd210406f]
also: [agent-evaluation]
---
Eval, synthetic-data, and RL-rollout batches alternate between inference and environment steps, so the serving layer and the environment pool set the finish time jointly. The paper coordinates three things:

- **Trajectory-aware routing** that keeps a sample on the worker holding its cache while balancing load.
- **A resource model** that sets sample concurrency to exploit parallelism without forcing recomputation.
- **Chain-Advancing Action Scheduling:** when environment capacity is tight, admit samples separately from environment execution and prioritize the longest chains to shorten the batch tail.

Live runs on BFCL, SWE-bench Multilingual, WideSearch, and MCP-Atlas cut makespan by 10.4% to 65.0% with evaluation scores unchanged. Reported by the team that trains the Ling-3.x models, on their own stack.
