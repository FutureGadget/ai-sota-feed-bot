---
slug: agent-benchmarks
kind: solution
title: "Agent benchmarks: fixed tasks that exercise real tool use"
status: active
obstacles: [agent-evaluation]
related_storylines: []
evidence: []
updated: 2026-10-06
themes:
  - key: trusting-the-score
    title: "What a score measures: model, harness, or noise"
    summary: Harness choice, protocol artifacts, and run-to-run noise can outweigh model differences; fixed environments, replays, counterfactual checks, and paired statistical trials are how scores earn trust.
  - key: own-workload
    title: Benchmarking on your own tools and real work
    summary: Public leaderboards overstate out-of-distribution performance; suites built from your own tools, real sessions, and held-out environments predict production better, and authoring them is getting cheaper.
  - key: domain-suites
    title: Domain-specific suites mined from real work
    summary: New suites target one job at a time (Java migration, Stripe integrations, AWS operations, Rails, code review, scientific imaging) and keep finding domain-specific failures, often in validation rather than code generation.
  - key: adversarial-and-security
    title: Adversarial tools, poisoned inputs, and security
    summary: Benchmarks now test the failure path (unreliable tools, poisoned business data, malicious issues) and score defenses on precision and recall together; cost-optimized models fail these far more often.
  - key: long-horizon-and-subsystems
    title: Long horizons and subsystem diagnostics
    summary: Long-horizon suites show final-answer scores overstate success, while subsystem benchmarks (memory, knowledge conflicts, root-cause reasoning, coordination) grade the inner process so a regression can be localized.
---

## TL;DR
Pin down a fixed set of tasks with known good outcomes and run agents against
them repeatedly. Unlike model benchmarks, agent benchmarks have to exercise
*tool use and multi-step trajectories* (booking, querying, fixing,
coordinating), so they double as integration tests for the whole agent, not
just the model.

## State of the art
Agent benchmarks now score the trajectory, not only the final answer: which
tools were called, whether the task was really done, and whether each
intermediate step was right.

**Public scores transfer poorly.** Agents that top familiar leaderboards
degrade sharply in unfamiliar environments, so the strongest signal comes from
suites built on your own tools and real sessions. Authoring them is getting
cheaper through small CLIs, standing workbenches, and automated task curation.

**The harness is part of what you measure.** A deliberately simple loop
reaches SOTA across 21 models, and the same model can gain inside one
commercial harness and lose inside another. Run-to-run noise compounds this:
one practitioner measured a model's own variance as larger than the
best-to-worst model gap. Credible results now come with fixed environments
(signed bundles, full replays), cost per solved task, repeated runs, and
checks against harness gaming.

**Suites are fragmenting by domain and failure mode.** Each new suite targets
one job and keeps finding domain-specific failures, often in validation rather
than code generation. Adversarial suites test the failure path: unreliable
tools, poisoned business data, malicious issues. Cost-optimized models fail
these far more often than frontier ones.

**Long horizons expose what short tasks hide.** Over hundreds of turns,
agents skip checks they planned themselves; on long multimodal research chains
the best system reaches 43.1% accuracy. Subsystem benchmarks (memory,
knowledge conflicts, root-cause reasoning) localize the part that broke.

**The open problem is validity.** A score is a claim about one task set,
harness, and protocol, and protocol artifacts can masquerade as capability.
Elastic's production harness shows what trusting a benchmark costs: paired
trials, significance tests against a measured noise floor, guard workloads,
and human approval gates.

## Trade-offs
A fixed benchmark is reproducible and cheap to re-run, but it is a static
target: agents over-fit to it, it goes stale as tools change, and "passing"
can mean "memorized the distribution."

A benchmark built on your own tooling is more predictive but is real work to
author and maintain. Small task sets have high variance: swapping a few tasks
out of a ~100-task set can flip which model ranks first, so a single number is
a claim about that task set, not a general fact about the model.

Best as a regression gate that catches known failures. Complement it with
[LLM-as-judge](/topic/llm-as-judge) on live traces for the open-ended cases a
fixed suite can't enumerate.

## Why it matters for platform engineers
Agent benchmarks are the CI gate of the agent stack: a fixed suite you run on
every prompt, model, harness, or tool change to catch regressions before users
do.

The leverage is building it from *your* environment and tools, because public
leaderboards systematically overstate how an agent will do on your workload.
Budget the upkeep and repeated runs too: a benchmark is only useful while it
still resembles production and its noise is smaller than the change you are
trying to detect.
