---
title: "Strands Evals turns a failed trace into categorized failures with a causal chain"
date: 2026-06-19
theme: grading-trajectories
evidence: [12500c0bbe5e4d6f]
---
AWS's Strands Evals detectors read a full agent trace and return **categorized failures** with confidence scores, causal chains linking a root cause to downstream symptoms, and a fix recommendation that says whether the change belongs in the system prompt or the tool definitions.

For agent evaluation, the output moves from a pass/fail number to a step-level diagnosis an engineer can act on. See [LLM-as-judge](/topic/llm-as-judge) for the judging side.
