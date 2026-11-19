---
title: "TRACE-MAS localizes multi-agent failures to the message or dependency that caused them, +60.2% accuracy"
date: 2026-11-19
theme: agentic-rca
evidence: [31fa9cd8fb58d57c]
also: [multi-agent]
---
Agent-level anomaly detectors flag which agent looks wrong, but in multi-agent systems the fault often sits in an interaction. TRACE-MAS learns normal execution from benign trajectories and detects deviations in **agent state changes, message transitions and task-dependency evolution**. It then attributes the failure to a source element and picks a minimal intervention to restore collaboration.

Across five MAS benchmarks, the authors report root-cause localization accuracy up **60.2%** over strong safeguards, plus consistent task-recovery gains. For builders: trace messages and dependency edges as first-class spans, or root-cause analysis can only blame agents.
