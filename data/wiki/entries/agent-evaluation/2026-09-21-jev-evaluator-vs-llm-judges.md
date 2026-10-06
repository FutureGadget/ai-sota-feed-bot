---
title: "Jev ships in LangSmith Evals as a faster, cheaper alternative to LLM judges"
date: 2026-09-21
theme: grading-trajectories
evidence: [d1454c52da381c41, 4c4569a7037ff789]
also: [llm-as-judge]
---
LangChain tested TypeSafe AI's **Jev** ("System One" models) as a judge against LLM judges on **accuracy, repeatability, latency, and cost**, then shipped it as a judge option in LangSmith Evals for production runs, datasets, and regression tests.

Repeatability is the axis to watch: an evaluator that returns the same verdict on the same trace makes regression tests meaningful. This is a competing architecture, not a validation method for the LLM-judge default. The comparison is vendor-run.
