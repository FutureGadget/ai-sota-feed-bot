---
slug: cost-controls
kind: solution
title: "Cost controls: budgets, metering, and per-task attribution"
status: active
obstacles: []
related_storylines: []
evidence: [450d5ccfb1602dc2, 00f3793762a13f49, e0a1d0978e9e8c3b, 4235792e910ea51a, 1c2693c60a919d8d, edd85739d7d91365, b4e45006617c01bc, a495552f9c306031, 483f6bab97830d53, 2b7c41257a8bc7e4, 68551dc8cb2a5ed6, 2d5ee61a05111f0a, cfb845e72338fcf2, 31d0f6b1d6dddfa7, 09d0c8e5c7031ff7, 136f83bb402008db]
updated: 2026-08-26
covers_evidence: [450d5ccfb1602dc2, 00f3793762a13f49, e0a1d0978e9e8c3b, 4235792e910ea51a, 1c2693c60a919d8d, edd85739d7d91365, b4e45006617c01bc, a495552f9c306031, 483f6bab97830d53, 2b7c41257a8bc7e4, 68551dc8cb2a5ed6, 2d5ee61a05111f0a, cfb845e72338fcf2, 31d0f6b1d6dddfa7, 09d0c8e5c7031ff7, 136f83bb402008db]
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
a console. Cost *estimates* themselves are getting more accurate, not just
more visible: Claude Code's `/cost`, status line, and `--max-budget-usd` now
factor in the 1.1x US-only-inference premium for data-residency workspaces,
closing a gap where the estimate a team budgets against didn't match what a
residency-constrained workspace actually pays.

Google Cloud is the third major vendor to ship this shape, and goes further
on flexibility than the other two: Gemini Enterprise adds a pay-as-you-go
tier with no upfront commitment alongside the existing per-seat
subscription, Flexible Savings Plans give spend-based discounts (10% at one
year, 20% at three) with no minimum or maximum commitment, and cost
governance ships as three concrete controls rather than one dashboard —
early anomaly detection that names the root cause and top three SKUs
driving a spike, project-level spend caps that pause API calls at a hard
monthly limit (with alerts at 50/80/100%), and a coming deferred-execution
mode that runs eligible agent workloads in off-peak capacity windows for up
to 50% off inference cost. It's the same "meter and cap" shape OpenAI and
Anthropic already ship, with anomaly root-causing and off-peak scheduling
as two levers neither of the other vendors' offerings include yet.

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
each team has to discover. Caching only pays off when it actually fires,
though: Claude Code shipped a fix for prompt caching silently breaking on
sessions routed through an LLM gateway or a custom base URL — a reminder
that a caching default is a piece of infra with its own failure mode, not a
one-time setting a team can stop verifying once it's on.

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

**Pre-filtering before the agent call is a cost control in its own right**,
not just a caching or routing knob: a Google Dataflow pattern combines a
managed streaming-execution service (Apache Beam) with the Agent Development
Kit so a real-time pipeline only escalates an event to a full gen-AI agent —
with database lookups and email tools attached — when the event actually
needs that judgment, instead of sending every raw event through a heavyweight
model call. It attacks the same scale/latency/cost blowup this page's
caching and routing entries address, but at the entry point to the agent
rather than inside its own loop.

**Agent-initiated payments are becoming their own budget surface**, not just
LLM token spend: AWS's AgentCore Payments middleware lets a LangChain agent
pay third-party APIs directly, signing x402-protocol payments against a
deterministic per-session budget rather than handing the agent an open
credential, with every payment traced through LangSmith — extending "meter
and cap" from model calls to the agent's own outbound spending on the
services it calls.

## What's new
Google Cloud becomes the third major vendor to ship a full FinOps-for-agents
surface: a no-commitment pay-as-you-go tier alongside the existing per-seat
plan, spend-based Flexible Savings Plans, anomaly detection that names a
spike's root cause and top offending SKUs, hard project-level spend caps
with staged alerts, and a coming off-peak "deferred execution" discount of
up to 50% (see State of the art above).

Prior update: Two Claude Code fixes sharpen the reliability of controls this page already
tracks rather than adding a new one: `/cost`, the status line, and
`--max-budget-usd` now include the 1.1x US-only-inference premium so budget
estimates match what a data-residency workspace actually pays, and a fix for
prompt caching silently breaking on gateway/custom-base-URL sessions closes
a gap where the caching default this page relies on could stop firing
without a visible signal.

Prior update: A Google Dataflow + Agent Development Kit pattern moves cost control to the
**entry point** of a streaming pipeline: only escalate an event to a full
gen-AI agent when it actually needs that judgment, instead of routing every
raw event through a heavyweight model call (see State of the art above).

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
