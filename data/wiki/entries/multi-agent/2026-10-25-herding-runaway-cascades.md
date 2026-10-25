---
title: "Multi-agent LLM systems herd and cascade when agents respond to each other's choices"
date: 2026-10-25
theme: oversight-and-safety
evidence: [f2df794e6fc1e504]
---
A paper studies LLM multi-agent systems in which agents react to each other's choices. That creates endogenous feedback loops, and the authors report vulnerability to social influence, herding, and runaway cascades. The failure is collective: a few early outputs can steer the rest of the group.

This is paper-reported, based on an excerpt of the abstract, so check the full text before relying on specific rates.

For builders: agents that see peers' answers before deciding are not independent votes. Where you use agent ensembles or debate for reliability, keep voters isolated, or add an independent check, rather than letting each agent condition on the others.
