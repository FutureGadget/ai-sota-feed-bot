---
title: "Voice agents get graded on execution, task outcome, and caller experience together"
date: 2026-08-12
theme: grading-trajectories
evidence: [dba85089f97f973f]
---
LangChain's guide to evaluating **voice agents** in LangSmith scores three layers together: execution, task outcome, and caller experience, using traces, code evaluators, LLM judges, and human review.

Voice adds turn-taking, latency, and interruption failures that a text transcript hides, so the trajectory grading used for text agents has to extend to timing. See [agent observability](/topic/agent-observability).
