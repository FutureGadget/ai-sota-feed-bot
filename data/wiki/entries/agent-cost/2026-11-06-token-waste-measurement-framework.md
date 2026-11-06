---
title: "LLM-judged token-waste spans let agents drop 41-46% of reasoning with little accuracy loss"
date: 2026-11-06
theme: harness-and-context
evidence: [61ea308958ff18b1]
---
A paper (paper-reported) records full agent trajectories, has an LLM judge mark removable spans, then validates them by deleting the spans and resuming execution. In online pruning on two agent benchmarks it removed **41-46% of the model's reasoning** while largely preserving task performance.

Waste varied more across tasks and agent settings than across models, and different harnesses added distinct inefficiencies under the same model and task. Reasoning and visible execution wasted tokens differently.

Aggregate token counts hide this structure. Measure waste per task and per harness before choosing a cheaper model; the harness may be the larger lever.
