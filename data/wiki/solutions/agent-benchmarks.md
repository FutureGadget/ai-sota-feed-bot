---
slug: agent-benchmarks
kind: solution
title: "Agent benchmarks: fixed tasks that exercise real tool use"
status: active
obstacles: [agent-evaluation]
related_storylines: [deep-research]
evidence: [432c23c0dd1c00f1, f07b6a3f3f344020, 55809dc9368e7936, 8f76e67ad854a6c0, 64ad8e685ed41a9b, 3abcf8c08cb66506, e214c4d6ded906fa, 4500a2b43ff7ed73]
updated: 2026-06-24
covers_evidence: [432c23c0dd1c00f1, f07b6a3f3f344020, 55809dc9368e7936, 8f76e67ad854a6c0, 64ad8e685ed41a9b, 3abcf8c08cb66506, e214c4d6ded906fa, 4500a2b43ff7ed73]
---

## TL;DR
Pin down a fixed set of tasks with known good outcomes and run agents against
them repeatedly. Unlike model benchmarks, agent benchmarks have to exercise
*tool use and multi-step trajectories* — booking, querying, fixing, coordinating
— so they double as integration tests for the whole agent, not just the model.

## State of the art
Two themes dominate. First, **benchmark what the agent did**, not just its answer:
rubric-style suites score whether the right tools were called and the task was
actually completed, and structural benchmarks probe specific failure axes (e.g.
DPBench on the determinants of multi-agent coordination). Second, **measure
capability on your own tooling and out of distribution**: Hugging Face's "is it
agentic enough" workbench benchmarks open models against the caller's actual
tools, and "Running the Gauntlet" shows agents that top familiar leaderboards
degrade sharply in unfamiliar environments — so a high public score is weak
evidence for your workload. Reusable eval workbenches (olmo-eval) package this
into the model/agent development loop so benchmarking is a standing harness, not
a one-off. A third theme is **the harness is part of what you benchmark**: a
cross-harness study reports a deliberately simple agent loop reaching SOTA across
21 models on SWE-pro and Terminal-Bench-style suites, evidence that elaborate
scaffolding often adds cost and variance without adding capability — so the
benchmark should hold the harness fixed and let it earn its complexity. A fourth
theme makes the "build it from your own environment" push concrete: rather than
synthetic tasks, the newest suites are **mined from real sessions** —
EnterpriseClawBench builds enterprise-agent tasks from actual workplace sessions
where an agent reads heterogeneous files, calls tools, and has to deliver a
business artifact, so the benchmark inherits the messiness of production instead
of approximating it. The flip side of trusting a benchmark is **reproducibility**:
because agent runs touch the network, filesystem, and shifting tool versions, a
score only means something if the environment is fixed — Proctor packages
coding-agent benchmarks as *signed, isolated bundles* so a run can be reproduced
(and a leaderboard claim audited) rather than taken on faith.

## What's new
Two moves toward trustworthy agent benchmarks: suites mined from **real sessions**
(EnterpriseClawBench builds enterprise-agent tasks from actual workplace sessions
— heterogeneous files, tool calls, a real artifact to deliver) so the benchmark
inherits production messiness, and **reproducible packaging** (Proctor ships
coding-agent benchmarks as signed, isolated bundles) so a score can be re-run and
a leaderboard claim audited. Both reinforce the standing lessons that public
scores over-state real-workload performance and that the harness itself is a
benchmark variable.

## Trade-offs
A fixed benchmark is reproducible and cheap to re-run, but it's a static target:
agents over-fit to it, it goes stale as tools change, and "passing" can mean
"memorized the distribution." Building a benchmark on your own tooling is more
predictive but is real work to author and maintain, and small task sets have
high variance. Best as a regression gate (catch known failures) — complement
with [LLM-as-judge](/topic/llm-as-judge) on live traces for the open-ended cases
a fixed suite can't enumerate.

## Why it matters for platform engineers
Agent benchmarks are the CI gate of the agent stack: a fixed suite you run on
every prompt, model, or tool change to catch regressions before users do.
The leverage is building it from *your* environment and tools, because public
leaderboards systematically over-state how an agent will do on your workload —
and budgeting the upkeep, since a benchmark is only useful while it still
resembles production.
