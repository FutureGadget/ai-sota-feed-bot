---
slug: agent-observability
kind: obstacle
title: "You can't see why an agent did what it did"
area: observability
status: active
solutions: [agent-tracing]
obstacles: []
related_storylines: []
evidence: [5d7159ca706a44c0, 8d1dc5b79d8b1372, 345d694a3d9a314f, 274255c89788d5c4, b71a53d3b8d39831, 20ef04d4cce6eb8c, 1bfbb319ced0695a]
updated: 2026-07-02
covers_evidence: [5d7159ca706a44c0, 8d1dc5b79d8b1372, 345d694a3d9a314f, 274255c89788d5c4, b71a53d3b8d39831, 20ef04d4cce6eb8c, 1bfbb319ced0695a]
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

One concrete practitioner case shows the debugging payoff: Pendo used
LangSmith to trace its own product agent (Novus) from raw user-behavior and
session-replay data through to the code fix — trace-first debugging closing
the loop from symptom to root cause in a single production example. The
tool surface keeps widening too, with Foglamp a newly self-described,
dedicated agent-observability tool, and at least one eval runner is folding
observability in rather than treating tracing as a separate integration:
Harbor's unified stack for evaluating long-running agents plugs LangSmith
sandboxes and observability directly into the eval loop
(see [evaluation](/topic/agent-evaluation)).

## What's new
A concrete practitioner case study lands: Pendo traced its product agent
from user-behavior data to the actual code fix using LangSmith, one
production example of trace-first debugging closing the loop end to end.
The tool surface keeps widening (Foglamp, a new dedicated
agent-observability tool) and one eval runner (Harbor) is folding
observability in rather than treating tracing as separate — it plugs
LangSmith sandboxes and tracing directly into its eval stack for
long-running agents.

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
