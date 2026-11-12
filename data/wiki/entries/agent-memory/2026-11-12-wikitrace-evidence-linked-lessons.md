---
title: "Linking each stored lesson to its source trajectory lets the agent check it before acting"
date: 2026-11-12
theme: recall-and-curation
evidence: [6b202536a684fb26]
---
The WikiTrace paper targets memory-induced degradation: an agent fails a task it would solve without memory because it follows a wrong lesson or misapplies a valid one. Lessons are served without the trajectories they came from, so the agent cannot check them.

WikiTrace stores each lesson as a short insight linked to a summary of why the trajectory succeeded or failed, and to the raw trajectory. The agent starts from the insights and follows the links with terminal tools when an insight lacks detail, conflicts with another, or came from a failed task.

It beats existing memory approaches and an insights-only baseline on five agentic benchmarks while reducing degradation. Paper-reported.

For builders: keep provenance pointers on distilled memory, and measure tasks that memory breaks, not only tasks it fixes.
