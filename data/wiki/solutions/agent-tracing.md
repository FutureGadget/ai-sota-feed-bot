---
slug: agent-tracing
kind: solution
title: "Tracing and trace analysis for agent runs"
status: active
obstacles: [agent-observability]
related_storylines: []
evidence: [5d7159ca706a44c0, 8d1dc5b79d8b1372, b71a53d3b8d39831]
updated: 2026-07-04
covers_evidence: [5d7159ca706a44c0, 8d1dc5b79d8b1372, b71a53d3b8d39831]
---

## TL;DR
Capture every agent run as a structured trace — the prompts, tool calls, results,
retries, and sub-agent handoffs — in a common format, then analyze those traces to
find what broke and why. Tracing is the substrate that makes an agent debuggable,
evaluable, and operable instead of a black box that occasionally misbehaves.

## State of the art
Two layers are maturing. The **capture** layer is standardizing: OpenInference /
OpenTelemetry-style span schemas and trace stores (Langfuse, Arize) give a portable
record of a run, and lightweight setups fall back to plain JSONL so the trace isn't
locked to one vendor. The **analysis** layer is where the recent movement is: rather
than asking an engineer to scroll spans, tools run a model over the trace corpus to
cluster recurring failures and propose harness fixes — HALO is an open-source,
local example that ingests Langfuse/Arize/JSONL traces and uses an RLM-based engine
to find repeating failure patterns across runs. Managed platforms are pushing the
same pattern as a product: LangSmith's fleet on-call copilot triages alerts off
live traces and adds voice/trace debugging and experiment status tracking, turning
trace reading into an assistive workflow. The common direction is *trace-in,
explanation-out*: the trace is no longer just an audit log, it's the input to an
automated diagnosis loop.

Capture itself is starting to commoditize into a **zero-config** setup:
Foglamp has an agent auto-detect its own LLM calls and instrument them
without the developer touching config or code, then surfaces cost-per-call,
latency, and quality/eval scores on a dashboard — the same drop-in
instinct as commoditized sandboxing tools, applied to observability instead
of isolation.

## What's new
Tracing setup is getting a **zero-config** entrant: Foglamp auto-instruments
an agent's LLM calls without manual integration, trading configurability for
a one-step setup that surfaces cost, latency, and quality per call.

## Trade-offs
Tracing adds instrumentation overhead and storage, and high-cardinality traces get
expensive to retain and search at fleet scale — so retention, sampling, and PII
scrubbing become real decisions. Model-over-trace analysis is itself an
LLM-cost-and-reliability line item (the analyzer can be wrong or miss the rare
failure), and a vendor trace format can lock you in. Plain JSONL is portable but
shifts the analysis burden onto you. Best value comes from standardizing the
capture format early so the analysis layer — homegrown or managed — stays swappable.

## Why it matters for platform engineers
Traces are the agent equivalent of logs and metrics: the precondition for
[evaluation](/topic/agent-evaluation) (you grade trajectories you captured), for
[cost control](/topic/cost-controls) (per-step token attribution), and for incident
response (a replayable run). Owning a portable trace format and an analysis loop is
the difference between operating an agent and guessing at it.
