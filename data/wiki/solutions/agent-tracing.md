---
slug: agent-tracing
kind: solution
title: "Tracing and trace analysis for agent runs"
status: active
obstacles: [agent-observability]
related_storylines: []
evidence: []
updated: 2026-10-06
themes:
  - key: capture
    title: "Capturing the run: zero-config SDKs, platform spans, new modalities"
    summary: Capture is commoditizing into drop-in SDKs and platform-native spans and now covers voice; payload defaults, truncation, and per-span billing differ by integration, and latent multi-agent channels escape the span schema entirely.
  - key: storage
    title: Storing and searching traces at fleet scale
    summary: Vendors are hardening trace stores with inverted indexes over object storage and one table for traces plus evals, while self-owned archives in your own S3 bucket keep sessions portable.
  - key: diagnosis
    title: Reading and diagnosing traces
    summary: Tools now run a model over trace corpora to cluster failures and triage alerts, and viewers are moving to chat-style session threads and inline, query-backed visualizations.
---

## TL;DR
Capture every agent run as a structured trace — the prompts, tool calls, results,
retries, and sub-agent handoffs — in a common format, then analyze those traces to
find what broke and why. Tracing is the substrate that makes an agent debuggable,
evaluable, and operable instead of a black box that occasionally misbehaves.

## State of the art
Tracing now has three layers, and each moved this year.

**Capture is commoditizing.** OpenTelemetry/OpenInference-style span schemas are
the common format, zero-config SDKs instrument LLM calls without code changes,
and serving platforms such as Cloudflare emit agent spans (`invoke_agent`,
`execute_tool`, `tool_approval`) natively. Coverage is widening past text to
voice agents. The catch is in the defaults: payload recording, truncation, and
billing differ per integration, not per vendor.

**Storage is becoming real infrastructure.** Traces are large, nested JSON
documents, and searching them at fleet scale takes purpose-built indexes (an
inverted index over object storage) or one store for traces and eval results.
The self-owned alternative is a lossless archive in your own bucket, searchable
and exposed to agents over MCP.

**Analysis is where the movement is.** The pattern is trace-in,
explanation-out: a model reads the trace corpus, clusters recurring failures,
and proposes harness fixes, or triages an alert from live traces. Viewers are
getting more readable too: chat-style session threads instead of span trees,
and inline visualizations that render the actual query result so an engineer
can check what the agent claims.

**The open problem is completeness.** Traces are not lossless when payloads get
truncated, model-over-trace analyzers can miss the rare failure, and agents in
a multi-agent system can coordinate through hidden states that no
message-and-tool-call span records (see [multi-agent](/topic/multi-agent) and
[agent observability](/topic/agent-observability)).

## Trade-offs
Tracing adds instrumentation overhead and storage, and high-cardinality traces
get expensive to retain and search at fleet scale, so retention, sampling, and
PII scrubbing are real decisions. They are not even consistent within one
platform: payload defaults can differ by SDK, so "does this capture PII by
default" is answered per integration, not per vendor.

Model-over-trace analysis is its own LLM cost and reliability line item; the
analyzer can be wrong or miss the rare failure. A vendor trace format can lock
you in, while plain JSONL is portable but shifts the analysis burden onto you.

Best value comes from standardizing the capture format early, so the storage
and analysis layers, homegrown or managed, stay swappable.

## Why it matters for platform engineers
Traces are the agent equivalent of logs and metrics: the precondition for
[evaluation](/topic/agent-evaluation) (you grade trajectories you captured), for
[cost control](/topic/cost-controls) (per-step token attribution), and for incident
response (a replayable run). Owning a portable trace format and an analysis loop is
the difference between operating an agent and guessing at it.
