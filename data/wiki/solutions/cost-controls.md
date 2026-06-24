---
slug: cost-controls
kind: solution
title: "Cost controls: budgets, metering, and per-task attribution"
status: active
obstacles: []
related_storylines: []
evidence: [450d5ccfb1602dc2, 00f3793762a13f49, e0a1d0978e9e8c3b, 4235792e910ea51a, 1c2693c60a919d8d]
updated: 2026-06-24
covers_evidence: [450d5ccfb1602dc2, 00f3793762a13f49, e0a1d0978e9e8c3b, 4235792e910ea51a, 1c2693c60a919d8d]
---

## TL;DR
Make agent spend observable and bounded: meter token usage per task, user, and
tool; attribute it to the unit of work (a request, a PR); set budgets and hard
caps so a runaway loop trips a limit instead of the invoice; and cut fixed
overhead with caching. These are the operational guardrails that sit *around* an
agent, complementing the architectural levers (compaction, topology, cheap
judges) that reduce the underlying token count.

## State of the art
The tooling is maturing from "read the monthly bill" toward continuous FinOps for
agents. Platform vendors ship **usage analytics plus enforceable spend controls**
(OpenAI's enterprise spend caps and analytics) so an org can set ceilings rather
than discover overruns. Developer tooling pushes **attribution** down to the unit
of work — Prtokens surfaces how many agent tokens a single pull request burned,
making cost a number on the artifact instead of an aggregate. **Caching** removes
repeated fixed cost: container/image caching (Amazon SageMaker) cuts cold-start
scaling cost and latency, and prompt/result caching trims repeated context. The
caching frontier is moving inside the model's own KV cache for **multimodal**
agents that re-examine the same frames, screenshots, and rendered artifacts every
look-back — Kamera proposes a position-invariant KV cache so those repeated visual
tokens are reused across context shifts instead of re-encoded from scratch,
turning redundant re-encoding (a hidden, fast-growing cost in agents that loop
over visual state) into a cache hit, training-free. The
load-bearing idea is that you cannot control what you don't meter, so per-task
metering and budgets are the foundation the architectural savings build on.

## What's new
Cost controls are shifting left: from a monthly finance review to per-task,
per-PR metering with enforceable caps (OpenAI spend controls, Prtokens
attribution) and caching that removes repeated fixed cost — turning agent cost
into a CI/ops signal you watch live rather than reconcile after the fact. Caching
is also reaching inside the model: Kamera's position-invariant KV cache lets
multimodal agents reuse the encoding of frames/screenshots they re-read every
step, cutting the redundant re-encode cost of visual look-backs without retraining.

## Trade-offs
Metering and attribution add plumbing (token accounting, tagging by task/user)
and only become actionable if someone owns the budgets. Hard caps protect spend
but can fail a legitimate long task at the worst moment, so they need graceful
degradation, not a hard kill. Caching saves money only when inputs actually
repeat and adds an invalidation/staleness problem of its own. And these controls
*bound* cost without lowering it — the real reductions come from the architecture
([compaction](/topic/context-compaction), [orchestration](/topic/agent-orchestration),
cheap judges), so controls are the floor, not the fix.

## Why it matters for platform engineers
This is FinOps for agents: the difference between a product with a known unit
economics story and one that quietly loses money per request. The actionable
stance is to meter every run, attribute cost to task and user, set budgets and
caps with sane fallback, and cache the repeatable — then use that visibility to
justify the architectural changes that actually move the bill.
