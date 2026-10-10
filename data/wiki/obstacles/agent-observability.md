---
slug: agent-observability
kind: obstacle
title: "You can't see why an agent did what it did"
area: observability
status: active
solutions: [agent-tracing]
obstacles: []
related_storylines: []
evidence: []
updated: 2026-10-10
themes:
  - key: trace-capture
    title: Capturing the full trajectory
    summary: Harnesses, serving platforms, and CLIs now emit agent spans natively over OpenTelemetry, across text and voice, but payload defaults, truncation, and retention vary by tool.
  - key: reading-traces
    title: Making traces readable and analyzable
    summary: Capture is no longer the bottleneck; models now read traces to surface failure patterns, and viewers present a session as one readable thread instead of a span tree.
  - key: agentic-rca
    title: Agents doing root-cause analysis and on-call
    summary: Production RCA and triage agents work when telemetry is pre-correlated and a human approves changes; benchmarks show end-to-end oncall accuracy is still low.
  - key: telemetry-ownership
    title: Where agent telemetry lives
    summary: Enterprises want traces and spend data inside their own network, answered either by self-hosted gateways or by managed platforms deployed into the customer's cloud.
  - key: monitoring-limits
    title: When the trace is not enough
    summary: Offline monitoring covers agents you cannot instrument live, and latent-channel work shows a complete transcript can still miss how agents coordinated.
---

## TL;DR
When an agent does the wrong thing, the run behind it is a long,
non-deterministic chain of model calls, tool results, and intermediate
decisions, and most of it is invisible afterwards. Unlike a stack trace, an
agent's "why" is spread across a trajectory you didn't log in enough detail,
can't replay deterministically, and can't easily diff against a working run.

## State of the art
**Observability for agents is trace-first.** The unit captured is the full
trajectory: prompts, tool calls, results, retries, and subagent handoffs.
Harnesses and serving platforms now emit these spans natively over
OpenTelemetry, and capture extends to voice agents and plain CLIs.

**The bottleneck has moved from capture to reading.** Teams run a model over
the traces to surface recurring failure patterns, debug many coding agents in
one console, and read a session as a single thread instead of a span tree.
Loops and runaway spend show up in the same trace, so trace and cost views are
merging.

**Agentic root-cause analysis works with guardrails, not alone.** Production
systems pair pre-correlated telemetry with LLM analysis and keep a human
approving changes. Evidence suggests models can reason about a failure once
the context is assembled. The best frontier agent on a realistic oncall
benchmark still gets only about a quarter of root causes right, so the
pipeline, not the model, is the open problem.

**Ownership is a design choice.** Enterprises want traces and spend data in
their own network, through a self-hosted gateway or a managed platform
deployed into their cloud. Payload privacy defaults differ by framework, and
traces can be truncated.

**The trace has limits.** Offline monitoring covers agents you can't watch
live, and agents can coordinate through hidden states a transcript never
records. Evaluating the monitors is itself an [evaluation](/topic/agent-evaluation)
problem.

## Why it matters for platform engineers
You cannot operate what you cannot explain. Without trajectory-level traces, a
regression after a model upgrade, a silent tool failure, or a runaway loop
stays invisible until it shows up as cost or a user complaint, and you can't
reproduce it.

Observability is the precondition for the rest of the stack:
[evaluation](/topic/agent-evaluation) needs traces to grade,
[cost control](/topic/cost-controls) needs per-step attribution, and incident
response needs a replayable run. The build-vs-buy choice is whether to
standardize on a trace format and own the analysis, or adopt a managed
platform. Either way, check payload retention and truncation defaults: the
trace is the new log line, and it carries secrets.
