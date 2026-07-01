---
slug: llm-as-judge
kind: solution
title: "LLM-as-judge: model-graded evaluation of traces and outputs"
status: active
obstacles: [agent-evaluation]
related_storylines: []
evidence: [4235792e910ea51a, 12500c0bbe5e4d6f, c000018ba1f03575, c579e90dd1110817, 4e6b89625cd2f1df, cf0a37dd32efaf51]
updated: 2026-07-01
covers_evidence: [4235792e910ea51a, 12500c0bbe5e4d6f, c000018ba1f03575, c579e90dd1110817, 4e6b89625cd2f1df, cf0a37dd32efaf51]
---

## TL;DR
Use a model to grade a model: give an LLM the agent's output (or its full
trace), plus a rubric, and have it return a structured verdict. It scales the
judgment human raters can't keep up with — every production trace, every CI run —
and is the practical backbone of agent evaluation when answers are open-ended.

## State of the art
The pattern is maturing from "ask GPT to rate 1–5" toward **structured,
trajectory-level judging**: detectors that read a trace and emit categorized
failures with confidence scores and causal chains (AWS's Strands Evals) rather
than a single scalar. The headline cost problem — running a frontier judge over
every trace is expensive — is being attacked by **fine-tuning small open judges
on production traces**: LangChain and Fireworks report matching frontier-judge
quality at roughly 1/100th the cost by mining perceived-error signals from real
traffic. A related frontier is judging *before* deployment — OpenAI's deployment
simulation predicts model behavior on real conversation data pre-release, using
model-graded simulation as a forecasting tool rather than a post-hoc check. The
counterweight to all of this is **judge auditing**: BabelJudge quantifies how
unreliable judges are across languages and agent trajectories — position bias
(favoring slot A), verbosity bias, and language-dependent drift that raw accuracy
masks — making "validate the judge" a measurable step, not a caveat. The practical
read is that a fine-tuned or frontier judge is only as trustworthy as the
bias-and-agreement numbers you can show against held-out human labels. The
cost/latency lever extends to the judge's *architecture*, not just its size: for
the high-volume safety-judging case, "Do Encoders Suffice?" systematically compares
encoder-based classifiers against decoder (generative) judges and finds that for
guardrail-style verdicts a cheaper, lower-latency encoder can often match the
generative judge — so the choice isn't only frontier-vs-fine-tuned-decoder but
also decoder-vs-encoder when you need a fast, inline safety check rather than a
free-text explanation. The cheap-judge trend now goes further than one classifier
per signal: Morph Reflexes reads an agent trace once through a shared backbone
and scores *many* behavioral signals (looping, reasoning leakage, user
frustration) with separate classifier heads off the same forward pass, reusing
KV-cache and compute across heads to hit sub-30ms inference and under 2ms of
marginal latency per additional signal — turning "judge every behavioral failure
mode" from N separate model calls into one shared-compute read of the trace.

## What's new
Judge auditing is catching up with judge adoption: BabelJudge puts numbers on
position, verbosity, and cross-language bias in LLM-as-judge over agent
trajectories, reinforcing that a cheap fine-tuned judge still has to clear a
measured bias-and-agreement bar before you trust it. That sits next to the
ongoing cost story — teams fine-tune a small open model on their own production
traces to recover near-frontier quality at a fraction of the cost — which now
extends to judge *architecture*: "Do Encoders Suffice?" finds an encoder
classifier can match a decoder judge for high-volume safety verdicts, a cheaper,
lower-latency option when you need an inline guardrail rather than a written
rationale. Morph Reflexes pushes the same architecture lever further by sharing
one backbone's compute across many classifier heads instead of running separate
small models per behavioral signal, reporting sub-30ms and near-zero marginal
latency per extra signal — multi-signal trace judging as a shared-compute
problem, not a per-signal model-count problem.

## Trade-offs
The judge is itself a non-deterministic model: it has biases (verbosity,
position, self-preference), can be gamed, and needs its *own* validation against
human labels or it just launders noise. Cheap fine-tuned judges narrow the cost
gap but can overfit to the trace distribution they were trained on and miss novel
failure modes. Best when paired with a rubric and a held-out human-labeled set,
and when you care about explanations (which step failed) rather than a single
opaque score.

## Why it matters for platform engineers
This is what makes continuous agent eval affordable: a judge you can run in CI
and on live traffic to catch regressions a model upgrade or prompt change
introduces. The cost knob (frontier vs. fine-tuned local judge) is a real
budget decision, and the judge becomes a dependency you must monitor and
re-validate like any other piece of infra. Pairs with
[agent benchmarks](/topic/agent-benchmarks) for the fixed-task side of evaluation.
