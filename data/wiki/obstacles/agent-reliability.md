---
slug: agent-reliability
kind: obstacle
title: "Agents give fluent, confident-looking output even when it's wrong"
area: reliability
status: stub
solutions: []
obstacles: []
related_storylines: []
evidence: [ed7d246a0b0ba7d9, b29eda10951194a9]
updated: 2026-07-07
covers_evidence: [ed7d246a0b0ba7d9, b29eda10951194a9]
---

## TL;DR
An agent can hallucinate a fact, skip a step, or misuse a tool and still
return a fluent, confident-looking answer — nothing about the output itself
signals that it's wrong. Deciding where to trust the model's own reasoning
versus routing to a deterministic tool, and getting an agent to actually
prove its work rather than just claim success, is a distinct engineering
problem from measuring that work after the fact (see
[agent evaluation](/topic/agent-evaluation)).
