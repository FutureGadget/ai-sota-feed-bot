---
slug: agent-observability
kind: obstacle
title: "You can't see why an agent did what it did"
area: observability
status: active
solutions: [agent-tracing]
obstacles: []
related_storylines: []
evidence: [5d7159ca706a44c0, 8d1dc5b79d8b1372, 345d694a3d9a314f, 274255c89788d5c4, c9f72591463a51bb, 863330601bd5d524, 34b461bf5b9be5ff, 38f362bfcba6a0fa, dcbc4c8f98ebc760, d0a4ccb3646c79ad]
updated: 2026-07-23
covers_evidence: [5d7159ca706a44c0, 8d1dc5b79d8b1372, 345d694a3d9a314f, 274255c89788d5c4, c9f72591463a51bb, 863330601bd5d524, 34b461bf5b9be5ff, 38f362bfcba6a0fa, dcbc4c8f98ebc760, d0a4ccb3646c79ad]
---

## TL;DR
When an agent does the wrong thing, the run that produced it is a long,
non-deterministic chain of model calls, tool results, and intermediate decisions —
and most of that is invisible after the fact. Unlike a stack trace, an agent's
"why" is spread across a trajectory you didn't log in enough detail, can't replay
deterministically, and can't easily diff against a working run. Debugging an agent
is increasingly the job, not a footnote to it.

## State of the art
Observability for agents is splitting from generic APM into a **trace-first**
discipline: the unit you capture is the full trajectory (prompts, tool calls,
results, retries, sub-agent handoffs), and the work is making that trajectory
queryable, diffable, and explainable. Tooling is consolidating around a common
trace format and then layering analysis on top — open-source debuggers ingest
traces from the emerging standards (Langfuse, Arize/OpenInference, or plain JSONL)
and run a model *over the traces themselves* to surface recurring failure patterns
rather than make an engineer read every span (HALO). Vendors are pushing the same
idea up the stack into managed triage: LangSmith now ships a fleet on-call copilot
for alert triage and dedicated voice/trace debugging, treating "read the traces and
tell me what's breaking" as an agentic product rather than a dashboard. A second
front is **monitoring agents you can't fully trace at runtime** — offline behavior
monitoring evaluates internal agents from logged activity after the fact, which
matters when live instrumentation is incomplete or the agent runs where you can't
watch it. The hard, still-open part is *evaluating the monitoring itself*: a
multi-dataset benchmark for LLM agents in microservice failure diagnosis (AgentOps)
exists precisely because "did the agent correctly diagnose the failure" is itself a
trajectory-grading problem over multimodal observability data — so agent
observability and [evaluation](/topic/agent-evaluation) are converging, with the
trace as the shared substrate.

Instrumentation is also showing up **inside the coding-agent product itself**,
not just in third-party observability tooling: Claude Code now emits
`workflow.run_id` and `workflow.name` as OpenTelemetry attributes, so a
multi-agent workflow run is traceable through the same OTel pipeline a team
already operates for the rest of its stack, rather than requiring a bespoke
exporter. Enterprise case studies are catching up to the same convergence
from the ops side: Schneider Electric built its LLMOps foundations on
LangSmith specifically to unify observability, evaluation, and deployment at
scale — a real deployment of the "trace as shared substrate" idea, not just a
vendor pitch for it.

Trace debugging is also going **cross-vendor**: LangSmith now positions
itself as the debug console for whichever coding agent a developer reaches
for — Claude Code, Codex, Cursor, or Copilot — inspecting tool calls,
sub-agent handoffs, errors, cost, and retries in one place instead of reading
each tool's own logs, treating "which agent produced this trace" as a detail
the observability layer should abstract away.

A **self-hosted control-plane** pattern is emerging alongside the managed
vendors above: AWS's Claude Apps Gateway is a stateless container an
organization runs itself in front of Claude Code/Desktop, relaying
per-request usage metrics to the team's own OpenTelemetry collector
(CloudWatch, Prometheus) while enforcing YAML-defined spend caps by org,
group, or user — folding telemetry relay and cost policy into one
customer-owned layer instead of a vendor dashboard.

Trace-first observability is also widening to a **new modality**: LangSmith
now traces voice agents built on Pipecat, LiveKit, OpenAI Realtime, and
Gemini Live, capturing audio, STT/TTS latency, interruptions, and tool calls
in one trace — the same trajectory-capture discipline this page tracks for
text-based agent loops, extended to the turn-taking and latency-sensitive
failure modes specific to a spoken interface (see
[agent latency](/topic/agent-latency) for why voice has a harder real-time
floor than text).

A named enterprise deployment backs the trace-plus-LLM-analysis pattern with
a production system: Expedia's STAR (built on FastAPI, Datadog, Celery,
Redis, and Langfuse) ingests service telemetry during live incidents, runs it
through structured workflows to generate root-cause assessments, and keeps
engineers in the loop for the final call rather than auto-resolving — an
instance of the trace-first, agentic-analysis pattern (HALO, LangSmith's
on-call copilot) built on infrastructure a platform team already runs, not a
new observability product.

## What's new
Expedia's STAR gives the trace-plus-agentic-analysis pattern a named
production deployment: built on FastAPI, Datadog, Celery, Redis, and
Langfuse, it analyzes telemetry during live incidents and generates
root-cause assessments while keeping engineers in the loop, running on
infrastructure most platform teams already operate rather than a dedicated
observability product.

## Why it matters for platform engineers
You cannot operate what you cannot explain. Without trajectory-level traces, a
regression after a model upgrade, a silent tool failure, or a runaway loop is
invisible until it shows up as cost or a user complaint — and you have no way to
reproduce it. Observability is the precondition for the rest of the stack:
[evaluation](/topic/agent-evaluation) needs traces to grade,
[cost control](/topic/cost-controls) needs per-step attribution, and incident
response needs a replayable run. The build-vs-buy question is whether to standardize
on a trace format and own the analysis, or adopt a managed platform — but either
way the trace is the new log line.
