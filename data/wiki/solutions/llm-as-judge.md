---
slug: llm-as-judge
kind: solution
title: "LLM-as-judge: model-graded evaluation of traces and outputs"
status: active
obstacles: [agent-evaluation]
related_storylines: []
evidence: [4235792e910ea51a, 12500c0bbe5e4d6f, c000018ba1f03575, c579e90dd1110817, 4e6b89625cd2f1df, cf0a37dd32efaf51, 5d87a279aac331cb, d8ea565801623af0, 4a0a79e7203bae64, 0570a6850cae75de]
updated: 2026-07-15
covers_evidence: [4235792e910ea51a, 12500c0bbe5e4d6f, c000018ba1f03575, c579e90dd1110817, 4e6b89625cd2f1df, cf0a37dd32efaf51, 5d87a279aac331cb, d8ea565801623af0, 4a0a79e7203bae64, 0570a6850cae75de]
---

## TL;DR
Use a model to grade a model: give an LLM the agent's output (or its full
trace) plus a rubric, and have it return a structured verdict. It scales the
judgment human raters can't keep up with — every production trace, every CI
run — and is the practical backbone of agent evaluation when answers are
open-ended.

## State of the art
The pattern is maturing from "ask GPT to rate 1–5" toward **structured,
trajectory-level judging**: AWS's Strands Evals reads a full trace and emits
categorized failures with confidence scores and causal chains, not a single
scalar.

**Cost** is the lever most teams are pulling first. Running a frontier judge
over every trace is expensive, so LangChain and Fireworks fine-tune small
open judges on production traces — mining perceived-error signals from real
traffic to match frontier-judge quality at roughly 1/100th the cost.
LangChain frames the whole loop as **data mining, not labeling**: cluster
failures out of real traces first, fine-tune the cheap judge on those
clusters, then use it to hill-climb the agent — so what gets judged comes
from observed failure, not a rubric drafted before the traces existed.

That cost lever now extends to the judge's **architecture**, not just its
size. "Do Encoders Suffice?" compares encoder-based classifiers against
decoder (generative) judges and finds that for guardrail-style verdicts, a
cheaper, lower-latency encoder can often match the generative judge — the
right call when you need a fast, inline safety check rather than a
free-text explanation. Morph Reflexes pushes the same lever further: it reads
an agent trace once through a shared backbone and scores many behavioral
signals (looping, reasoning leakage, user frustration) with separate
classifier heads off the same forward pass, reusing KV-cache and compute to
hit sub-30ms inference and under 2ms of marginal latency per added signal —
turning "judge every failure mode" from N model calls into one shared-compute
read of the trace.

Judging is also moving **earlier**: OpenAI's deployment simulation runs
model-graded simulation over real conversation data to predict model
behavior before release, rather than only checking after deployment.

The counterweight to all of this speed-and-cost optimization is **judge
auditing**. BabelJudge quantifies how unreliable judges are across languages
and agent trajectories — position bias (favoring slot A), verbosity bias, and
language-dependent drift that raw accuracy masks. A fine-tuned or frontier
judge is only as trustworthy as the bias-and-agreement numbers you can show
against held-out human labels.

A sharper counterweight asks whether a judge is needed at all: for **stateful**
agent evaluation, a deterministic-replacement approach checks state
transitions directly rather than asking a model to grade them — when the task
admits a programmatic check, skipping the judge removes its bias, cost, and
non-determinism in one move. The practical reframe is to treat LLM-as-judge as
the fallback for open-ended, hard-to-specify outputs, not the default for
every evaluation.

A cheaper lever than a bigger judge is **ensembling smaller ones**: rather
than upgrading to a stronger single model, running independent judges under
different personas — including one deliberately briefed to argue the
opposite verdict — over the same artifact substantially cuts false
positives. A practitioner reports this "reasonable setup around the model"
lowers false-positive rates more reliably than swapping in a better model,
extending the standing cost lever (smaller fine-tuned judges, cheaper
encoders) with a quality lever that doesn't require a bigger model at all.

The auditing lens is also turning on the **rubric itself**, not just the
judge reading it. A meta-evaluation of LLM-generated grading rubrics — tested
across several generation setups and two model backbones on a paper-
reproduction eval task — validates rubrics against semantic similarity and
ground-truth scores, treating "is this rubric any good" as a distinct
failure surface from "is this judge biased": a well-calibrated judge can
still grade against a bad checklist.

## What's new
LangChain reframes judge fine-tuning as a **data-mining problem**: mine
production traces for failure clusters first, fine-tune the cheap judge on
those clusters, then hill-climb agent performance from that signal — the
same cost lever as before (small judge over frontier judge) but with the
training target derived from observed failures rather than a rubric.

Judge quality also gets a cheap lever that isn't "use a bigger model":
ensembling independent judge personas over the same artifact — including a
deliberately contrarian one — cuts false positives more reliably than
upgrading to a stronger single judge, alongside the standing deterministic
alternative for stateful tasks and BabelJudge's numbers on judge bias.

## Trade-offs
The judge is itself a non-deterministic model: it has biases (verbosity,
position, self-preference) and can be gamed. It needs its own validation
against human labels, or it just launders noise.

Cheap fine-tuned judges narrow the cost gap, but they can overfit to the
trace distribution they were trained on and miss novel failure modes.

Ensembling several judge personas cuts false positives but multiplies the
number of judge calls per artifact, trading judge-side cost for precision —
worth it only where false positives are expensive to triage by hand.

LLM-as-judge works best paired with a rubric and a held-out human-labeled
set, and when you care about explanations (which step failed) rather than a
single opaque score.

## Why it matters for platform engineers
This is what makes continuous agent eval affordable: a judge you can run in
CI and on live traffic to catch regressions a model upgrade or prompt change
introduces.

The cost knob — frontier judge, fine-tuned local judge, or encoder
classifier — is a real budget decision, and the judge itself becomes a
dependency you must monitor and re-validate like any other piece of infra.
Pairs with [agent benchmarks](/topic/agent-benchmarks) for the fixed-task
side of evaluation.
