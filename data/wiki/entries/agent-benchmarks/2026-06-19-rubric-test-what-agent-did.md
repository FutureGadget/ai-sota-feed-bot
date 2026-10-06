---
title: "Rubric tests what an agent did, not just what it said"
date: 2026-06-19
theme: own-workload
evidence: [55809dc9368e7936]
---
Rubric is an open-source tool that scores **an agent's actions**: whether it called the right tools and actually completed the task, not only whether its final answer reads correctly.

Grading the trajectory turns an agent eval into an integration test. A correct-sounding answer reached through the wrong tool calls fails.
