---
title: "A teardown of 12 public evals finds graders failing valid work in eight of them"
date: 2026-11-21
theme: trusting-the-score
evidence: [0ada1934a0788fbd]
also: [agent-evaluation]
---
Eugene Yan's teardown of twelve public evals (coding, science, knowledge work, browsing) found evidence in **eight of twelve** that the grader failed work that should have passed. Benchmarks now ship like software: Agents' Last Exam v1.1 **retired 30 tasks and revised 57**, and Terminal Bench drops saturated tasks per version, so scores from different releases are not comparable.

The recommendations: prefer deterministic checks over LLM judges, report reliability rather than average pass rate, and stop measuring cost in dollars alone. For builders: pin the benchmark version next to any score you quote, and read a sample of failed tasks before trusting a ranking.
