---
title: "Distributed-systems debugging benchmark: agents find the file but miss the causal code blocks"
date: 2026-11-14
theme: long-horizon-and-subsystems
evidence: [0218b1af8990e061]
also: [agent-observability]
---
DistDebug-Bench gives agents 120 real, closed failures from 11 production distributed systems, mostly logic, concurrency, and error-handling bugs. The agent gets the report, partial logs or stack traces, and the repository before the fix. It is scored on the diagnosis, not the patch, against human-labeled causal code blocks.

Failures surface far from their cause. In one ZooKeeper incident the report points at leader election, but the cause is a shutdown path that carries stale state into the next quorum.

Across the tested configurations, coverage falls **13-22 percentage points** when agents must name the causal blocks rather than the file. Results average three runs per incident with bootstrap confidence intervals.

For builders: "found the right file" overstates agentic root-cause analysis. Grade incident agents on causal precision.
