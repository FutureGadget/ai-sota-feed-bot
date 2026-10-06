---
title: "MACE organizes shared multi-agent memory into scored units and averages 81.11% on eight benchmarks"
date: 2026-09-21
theme: shared-memory
evidence: [9463df6fcb6ce102]
also: [multi-agent]
---
**MACE (Memory-Agent Co-Evolution)** turns a multi-agent system's collaboration traces into functional memory units: conditions, actions, and outputs linked by support, conflict, and repair relations. Within a memory budget it picks which units and formats (instructions vs. checklists) to hand each agent, and updates unit scores from task outcomes.

It averages **81.11% across eight benchmarks, beating ten baselines**. How shared memory is organized and presented back to agents is a tunable variable, not just whether writes conflict.
