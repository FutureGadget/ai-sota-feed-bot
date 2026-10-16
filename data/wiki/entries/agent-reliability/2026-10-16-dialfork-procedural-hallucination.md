---
title: "Procedural hallucination: fluent turns that leave the intended process"
date: 2026-10-16
theme: hallucination-containment
evidence: [8dd49219f40d9b76]
also: [agent-evaluation]
---
DialFork targets a failure factual checks miss: each utterance is fluent and plausible, but the dialogue drifts from the intended procedure. The benchmark forks conformant dialogues at chosen turns and injects one of four hallucination types, giving 36,278 dialogues across 24 tasks in 12 domains (30 annotators validated construction).

It defines three tasks: fleet-level deviation (monitoring deployed agents), single-dialogue deviation, and the turn where a dialogue first goes off-track (real-time guardrails). Its flow-aware FlowScore beat all baselines across seven encoders, which the authors read as semantic similarity being no substitute for procedural similarity. Paper-reported; MIT-licensed.

For builders running scripted workflows, monitor process adherence separately from factuality.
