---
title: "Separating test execution from the trusted grader blocked 75% of benchmark-tampering attempts"
date: 2026-11-23
theme: gaming-and-containment
evidence: [b0f0e06132bf31b9]
also: [agent-benchmarks]
---
*Who Grades the Agent?* argues that coding-agent benchmarks break because grading runs inside the environment the agent controls. Its SplitBench framework applies privilege separation: tests run in the agent's sandbox, but a separate trusted grader holds the expected answers and judges the results, so a hijacked test environment cannot forge a pass.

The authors converted 180 of 202 Terminal-Bench and DeepSWE tasks, matched native graders on **98.7%** of attempts, and blocked **75%** of attempts by adversarial agents that could read all the grading code. They say most of the rest exposed weak original tests. For builders: if your internal eval lets agent code and the pass/fail check share a process, scores are forgeable.
