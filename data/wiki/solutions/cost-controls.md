---
slug: cost-controls
kind: solution
title: "Cost controls: budgets, metering, and per-task attribution"
status: active
obstacles: []
related_storylines: []
evidence: []
updated: 2026-10-06
themes:
  - key: vendor-spend-controls
    title: Vendor consoles add analytics, entitlements, and spend caps
    summary: OpenAI, Anthropic, and Google Cloud now ship usage analytics with enforceable caps; Google adds anomaly root-causing and off-peak discounts, and estimates are getting more accurate.
  - key: attribution
    title: Attributing spend to the PR, the agent, and the anomaly
    summary: Open-source tools attribute agent tokens to a pull request or across every coding agent a developer runs, and AWS runs anomaly triage as a managed agent.
  - key: hard-caps
    title: Hard caps that run before the call, not after the bill
    summary: Budget checks are moving into the execution path, per process, per session, across multi-agent runs, and for agent-initiated payments, with calls to ship caps on by default.
  - key: caching-and-filtering
    title: Caching and pre-filtering cut fixed overhead
    summary: Prompt caching of the stable agent prefix is becoming a framework default and KV reuse extends to images, but caches fail silently and need monitoring.
---

## TL;DR
Make agent spend observable and bounded: meter token usage per task, user, and
tool; attribute it to the unit of work (a request, a PR); set budgets and hard
caps so a runaway loop trips a limit instead of the invoice; and cut fixed
overhead with caching. These guardrails sit *around* an agent, complementing
the architectural levers that reduce the underlying token count.

## State of the art
**Agent FinOps is moving from reading the monthly bill to enforcing limits in
the execution path.**

- **Vendor consoles** from OpenAI, Anthropic, and Google Cloud now pair usage
  analytics with enforceable caps and model-level entitlements. Google goes
  furthest, with anomaly detection that names the SKUs behind a spike,
  project caps that pause API calls, and off-peak discounts of up to 50%.
- **Attribution** is moving to the unit of work: tokens per pull request,
  cost across every coding agent a developer runs, and anomaly triage run by
  a managed agent.
- **Hard caps** are moving inside the agent. Budgets are checked before each
  model call, shared across processes through a common ledger, and extended
  to what an agent spends on paid APIs. The argument now is for caps that are
  on by default.
- **Caching** of the stable prompt prefix is becoming a framework default.
  Pre-filtering, so only events that need judgment reach an agent, cuts calls
  at the entry point.

**The consensus: you cannot control what you don't meter.** Per-task
metering is the base that architectural savings build on, and it is how a
team proves those savings happened.

**The open problems are accuracy and silent failure.** Cost estimates have
missed regional premiums, prompt caching has broken behind gateways without
warning, and the strongest savings claims from cap tooling come without
published methodology. Treat estimates, cache-hit rates, and caps as
monitored infrastructure, not settings.

## Trade-offs
Metering and attribution add plumbing (token accounting, tagging by task and
user) and only become actionable if someone owns the budgets.

Hard caps protect spend but can fail a legitimate long task at the worst
moment, so they need graceful degradation, not a hard kill.

Caching saves money only when inputs actually repeat, and it adds an
invalidation and silent-miss problem of its own.

Self-hosted routers and gateways remove vendor lock-in but move provider
integrations, updates, and uptime onto the team running them.

These controls *bound* cost without lowering it. The real reductions come
from architecture ([compaction](/topic/context-compaction),
[orchestration](/topic/agent-orchestration), routing, cheap judges), so
controls are the floor, not the fix.

## Why it matters for platform engineers
This is FinOps for agents: the difference between a product with known unit
economics and one that quietly loses money per request.

Meter every run, attribute cost to task and user, set budgets and caps with
sane fallback, and cache the repeatable. Then use that visibility to justify
the architectural changes that actually move the bill (see
[agent cost](/topic/agent-cost)) and to prove ROI per task (see
[proving agent ROI](/topic/proving-agent-roi)).
