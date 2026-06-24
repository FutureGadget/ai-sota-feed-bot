---
slug: agent-cost
kind: obstacle
title: "Agent token costs are unpredictable and easily run away"
area: cost
status: active
solutions: [cost-controls, context-compaction, agent-orchestration]
obstacles: []
related_storylines: []
evidence: [450d5ccfb1602dc2, 00f3793762a13f49, e0a1d0978e9e8c3b, 1c98fc492e1df243, 19e4caf222bfb0d9, 4235792e910ea51a, c32171008fef614c, 1c2693c60a919d8d]
updated: 2026-06-24
covers_evidence: [450d5ccfb1602dc2, 00f3793762a13f49, e0a1d0978e9e8c3b, 1c98fc492e1df243, 19e4caf222bfb0d9, 4235792e910ea51a, c32171008fef614c, 1c2693c60a919d8d]
---

## TL;DR
A chatbot turn costs a predictable number of tokens; an agent can loop, re-read
its whole context every step, spawn sub-agents, and call a model to grade its
own work — so the bill is a function of *behavior*, not request count, and a
single misbehaving run or a topology choice can multiply spend without anyone
noticing until the invoice arrives. Cost is the run-time obstacle that the
build-time decisions (memory, multi-agent, eval) silently determine.

## State of the art
Cost is being attacked on two fronts: **making it visible** and **making it
smaller**. Visibility is moving from a monthly surprise to a first-class signal —
enterprise platforms now ship usage analytics and hard spend controls (OpenAI's
enterprise spend caps), and developer tooling attributes cost down to the unit of
work, e.g. showing how many agent tokens a single pull request consumed
(Prtokens). The reduction side is the sum of the other obstacles' solutions:
keeping the working set small via [context compaction](/topic/context-compaction)
attacks the per-step token bill directly (the cost scales with context size);
choosing a cheaper [orchestration](/topic/agent-orchestration) topology matters
because the coordination structure dominates spend — Stanford's DeLM reports
cutting multi-agent task cost ~50% by dropping the central orchestrator; and even
evaluation is a cost line item, which is why teams fine-tune small judges to cut
trace-judging cost ~100×. Infra-level levers help too: container/image caching
(Amazon SageMaker) cuts cold-start scaling cost and latency, and inside the model,
KV-cache reuse cuts a cost specific to **multimodal** agents that re-read the same
frames or screenshots each step — Kamera's position-invariant cache reuses those
visual tokens across context shifts instead of re-encoding them every look-back.
A subtler driver is
the **context cost of instructions themselves** — every skill, hook, or subagent
you add to steer an agent consumes context budget, so steering and cost are the
same knob viewed from two sides. The flip side of that knob is the biggest single
lever: **spending context to downshift the model**. Cheap models are far cheaper
per token but ignore architecture rules — ANMA reports Claude Haiku 4.5 violating
its constraints in 13 of 19 runs unguided, but 0 of 20 once wrapped in explicit
boundary contracts (YAML rules plus `CLAUDE.md`, hooks, and CI checks) — so a bit
of contract overhead can make a cheaper model reliable enough to replace a
frontier one on the bulk of the work.

## What's new
Cost is becoming an explicit, measured surface rather than an after-the-fact
invoice: enterprise spend caps and usage analytics, per-PR token-cost attribution
(Prtokens), and a growing recognition that the cheapest lever is architectural —
decentralized topologies (DeLM, ~50% off), cheap fine-tuned judges (~100× off),
and contract layers that make a cheaper model obey rules well enough to downshift
to it (ANMA: Haiku rule-violations 13/19 → 0/20) rather than a smaller model
alone.

## Why it matters for platform engineers
This is the obstacle that turns a working demo into an unaffordable product. The
job is to make spend observable per task and per user, set budgets and caps
before a loop runs away, and treat the architecture (compact vs. retrieve,
single-agent vs. orchestrated, frontier vs. fine-tuned judge) as the primary cost
control — because the biggest savings come from *how* the agent is built, not
from shaving the model price. Cost, latency, and reliability trade against each
other, so the deliverable is a cost model you can reason about, not a one-time
optimization.
