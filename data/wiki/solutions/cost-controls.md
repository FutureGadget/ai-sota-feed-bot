---
slug: cost-controls
kind: solution
title: "Cost controls: budgets, metering, and per-task attribution"
status: active
obstacles: []
related_storylines: []
evidence: [450d5ccfb1602dc2, 00f3793762a13f49, e0a1d0978e9e8c3b, 4235792e910ea51a, 1c2693c60a919d8d, edd85739d7d91365, b4e45006617c01bc, a495552f9c306031, 483f6bab97830d53, 2b7c41257a8bc7e4, 68551dc8cb2a5ed6]
updated: 2026-08-08
covers_evidence: [450d5ccfb1602dc2, 00f3793762a13f49, e0a1d0978e9e8c3b, 4235792e910ea51a, 1c2693c60a919d8d, edd85739d7d91365, b4e45006617c01bc, a495552f9c306031, 483f6bab97830d53, 2b7c41257a8bc7e4, 68551dc8cb2a5ed6]
---

## TL;DR
Make agent spend observable and bounded: meter token usage per task, user, and
tool; attribute it to the unit of work (a request, a PR); set budgets and hard
caps so a runaway loop trips a limit instead of the invoice; and cut fixed
overhead with caching. These are the operational guardrails that sit *around* an
agent, complementing the architectural levers (compaction, topology, cheap
judges) that reduce the underlying token count.

## State of the art
The tooling is maturing from "read the monthly bill" toward continuous FinOps
for agents.

Platform vendors ship **usage analytics plus enforceable spend controls**
(OpenAI's enterprise spend caps and analytics) so an org can set ceilings
rather than discover overruns. Anthropic ships the same shape for Claude
Enterprise: richer admin analytics, model-level entitlements, and spend
alerts so admins track adoption and cap spend without building their own
metering layer. A published guide walks IT admins through that same
surface end-to-end: spend caps, model-level controls, usage analytics, and
cost-relevant API features like prompt caching and batch processing, as one
consolidated cost-visibility playbook rather than settings scattered across
a console.

Developer tooling pushes **attribution** down to the unit of work — Prtokens
surfaces how many agent tokens a single pull request burned, making cost a
number on the artifact instead of an aggregate. Third-party tooling is
filling the cross-agent gap too: Agentsview browses, searches, and tracks
cost across every AI coding agent a developer runs, aggregating spend no
single vendor's own dashboard shows.

The analysis step itself is being delivered as a **managed agent**: AWS's
FinOps Agent (public preview) automates the FinOps loop — investigating cost
anomalies and correlating spend changes with account activity — so anomaly
triage is continuous and queryable rather than a manual monthly dig.

**Caching** removes repeated fixed cost: container/image caching (Amazon
SageMaker) cuts cold-start scaling cost and latency, and prompt/result
caching trims repeated context. Prompt caching in particular is becoming an
automatic, framework-level default rather than a hand-tuned optimization —
LangChain's Deep Agents reports cutting LLM token cost by up to ~80% across
every major provider with no extra config, because an agent loop re-sends a
large, stable prefix (system prompt, tool schemas, prior steps) every turn,
which is exactly the input a provider prompt cache is built to discount. That
makes "cache the stable prefix" a default the framework owns, not a knob
each team has to discover.

The caching frontier is moving inside the model's own KV cache for
**multimodal** agents that re-examine the same frames, screenshots, and
rendered artifacts every look-back — Kamera proposes a position-invariant KV
cache so those repeated visual tokens are reused across context shifts
instead of re-encoded from scratch, turning redundant re-encoding (a hidden,
fast-growing cost in agents that loop over visual state) into a cache hit,
training-free.

**Self-hosted routing is a newer entry in the control set**: Millwright, a
Rust-based, self-hosted LLM router, is built specifically for cost savings
and transparency, launched as hosted routers proliferate (Ramp Router,
Vercel's AI Gateway) and OpenRouter itself faces a possible acquisition —
owning the routing layer gives a team the same visibility and control over
per-request model choice that metering gives over spend, without depending
on a vendor's continuity.

The load-bearing idea is that you cannot control what you don't meter, so
per-task metering and budgets are the foundation the architectural savings
build on.

## What's new
Self-hosted routing joins the toolkit: Millwright, a Rust-based, self-hosted
LLM router, positions itself as the cost-and-transparency alternative to
hosted routers (Ramp Router, Vercel's AI Gateway) at the moment OpenRouter
faces a possible acquisition — owning the routing layer instead of renting
it from a vendor subject to M&A.

## Trade-offs
Metering and attribution add plumbing (token accounting, tagging by
task/user) and only become actionable if someone owns the budgets.

Hard caps protect spend but can fail a legitimate long task at the worst
moment, so they need graceful degradation, not a hard kill.

Caching saves money only when inputs actually repeat and adds an
invalidation/staleness problem of its own.

Self-hosted routing (Millwright) removes hosted-router lock-in and M&A risk,
but shifts operational ownership — provider integrations, updates, uptime —
onto the team running it, the same trade-off self-hosted memory and
sandboxing stores make elsewhere in this wiki.

And these controls *bound* cost without lowering it — the real reductions
come from the architecture ([compaction](/topic/context-compaction),
[orchestration](/topic/agent-orchestration), cheap judges), so controls are
the floor, not the fix.

## Why it matters for platform engineers
This is FinOps for agents: the difference between a product with a known
unit economics story and one that quietly loses money per request.

The actionable stance is to meter every run, attribute cost to task and
user, set budgets and caps with sane fallback, and cache the repeatable —
then use that visibility to justify the architectural changes that actually
move the bill.
