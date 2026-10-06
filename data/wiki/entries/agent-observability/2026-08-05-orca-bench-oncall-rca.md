---
title: "ORCA-bench: the best frontier agent gets 25.3% of realistic oncall root causes right"
date: 2026-08-05
theme: agentic-rca
evidence: [135c077a65b61dda]
---
**ORCA-bench** pairs an OpenTelemetry-instrumented microservice testbed (six days of metrics, logs, and traces) with **1,079 oncall RCA tasks**, graded by an LLM judge that human SREs re-scored (κ=0.90). Across five frontier agents, the best accuracy is **25.3%** on realistic-input tasks and 10.0% on hard ones. The weakest model invents an implausible root cause on 40% of reports.

The authors read this as a lower bound on the real-world gap. The reasoning may be there, but the end-to-end oncall pipeline is mostly unsolved.
