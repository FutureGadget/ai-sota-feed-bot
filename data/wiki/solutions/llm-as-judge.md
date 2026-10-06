---
slug: llm-as-judge
kind: solution
title: "LLM-as-judge: model-graded evaluation of traces and outputs"
status: active
obstacles: [agent-evaluation]
related_storylines: []
evidence: []
updated: 2026-10-06
themes:
  - key: structured-verdicts
    title: From a 1-5 score to structured, trace-level verdicts
    summary: Judges now read whole trajectories and return categorized failures, run before release, or sit inside the agent loop as a grader.
  - key: cheaper-judges
    title: Making the judge cheap enough to run on every trace
    summary: Small fine-tuned judges, encoder classifiers, and shared-backbone heads cut judge cost and latency by one to two orders of magnitude.
  - key: trusting-the-judge
    title: Auditing the judge, the rubric, and whether you need one
    summary: Judges carry position, verbosity, and language bias, and rubrics can be wrong; calibrate against human labels or replace the judge with a deterministic check.
---

## TL;DR
Use a model to grade a model: give an LLM the agent's output (or its full
trace) plus a rubric, and have it return a structured verdict. It scales the
judgment human raters can't keep up with — every production trace, every CI
run — and is the practical backbone of agent evaluation when answers are
open-ended.

## State of the art
The pattern has moved past "ask a model to rate 1–5". Current judges read the
**whole trace** and return categorized failures with causes, and they now run
in three places: offline over production traces, before release in simulated
deployment, and inside the agent loop as a grader that sends per-criterion
feedback back to the agent.

**Cost is the first lever teams pull.** A frontier judge over every trace is
too expensive, so teams fine-tune small open judges on their own failure
clusters (about 1/100th the cost) or swap the generative judge for encoder
classifiers that score many signals in one pass.

**Trust is the open problem.** Judges show position, verbosity, and language
bias that raw accuracy hides, and an LLM-written rubric can be wrong even when
the judge is calibrated. The working practice: validate the judge against
held-out human labels, ensemble cheap judges to cut false positives, and use a
deterministic check instead of a judge whenever the task allows one.

## Trade-offs
The judge is itself a non-deterministic model: it has biases (verbosity,
position, self-preference) and can be gamed. It needs its own validation
against human labels, or it just launders noise.

Cheap fine-tuned judges narrow the cost gap, but they can overfit to the trace
distribution they were trained on and miss novel failure modes. Ensembling
judge personas cuts false positives but multiplies judge calls per artifact.

LLM-as-judge works best with a rubric, a held-out human-labeled set, and a
need for explanations (which step failed) rather than one opaque score.

## Why it matters for platform engineers
This is what makes continuous agent eval affordable: a judge you can run in CI
and on live traffic to catch regressions a model upgrade or prompt change
introduces.

The cost knob — frontier judge, fine-tuned local judge, or encoder classifier —
is a real budget decision, and the judge itself becomes a dependency you must
monitor and re-validate like any other piece of infra. Pairs with
[agent benchmarks](/topic/agent-benchmarks) for the fixed-task side of
evaluation.
