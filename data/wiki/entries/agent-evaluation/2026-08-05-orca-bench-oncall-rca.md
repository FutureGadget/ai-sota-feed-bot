---
title: "ORCA-bench: best agent gets 25.3% of realistic oncall root-cause tasks right"
date: 2026-08-05
theme: domain-benchmarks
evidence: [135c077a65b61dda]
---
**ORCA-bench** pairs a live, OpenTelemetry-instrumented microservice testbed with **1,079 root-cause-analysis tasks**, graded by an LLM judge that human SREs independently re-scored (κ=0.90).

Across five frontier agents, the best RCA accuracy is **25.3%** on realistic tasks and 10.0% on hard ones; the weakest hallucinates a root cause on 40% of reports. Don't hand oncall triage to an agent on the strength of coding scores. See [agent observability](/topic/agent-observability).
