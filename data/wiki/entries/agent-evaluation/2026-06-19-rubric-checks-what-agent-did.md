---
title: "Rubric checks what an agent did, not just what it said"
date: 2026-06-19
theme: grading-trajectories
evidence: [55809dc9368e7936]
---
Rubric, an open-source eval tool shown on Show HN, tests an LLM agent's **actions** — which tools it called and in what order — rather than only its final text answer.

It is a small example of the shift to trajectory evaluation: a correct-looking answer can come from a broken path, so the tool calls themselves need assertions.
