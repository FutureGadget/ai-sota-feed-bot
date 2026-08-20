---
slug: agent-observability
kind: obstacle
title: "You can't see why an agent did what it did"
area: observability
status: active
solutions: [agent-tracing]
obstacles: []
related_storylines: []
evidence: [5d7159ca706a44c0, 8d1dc5b79d8b1372, 345d694a3d9a314f, 274255c89788d5c4, c9f72591463a51bb, 863330601bd5d524, 34b461bf5b9be5ff, 38f362bfcba6a0fa, dcbc4c8f98ebc760, d0a4ccb3646c79ad, bda1da8f5bc3b679, 363d53a23c23f150, 135c077a65b61dda, 6a2c44f62f58bd05, 0c557d74dd5dcc14, 19b2c00e70a40ab1, f07f7955a1ecbd39, 0ada5d894838d46e, dadedf10efb45ade]
updated: 2026-08-20
covers_evidence: [5d7159ca706a44c0, 8d1dc5b79d8b1372, 345d694a3d9a314f, 274255c89788d5c4, c9f72591463a51bb, 863330601bd5d524, 34b461bf5b9be5ff, 38f362bfcba6a0fa, dcbc4c8f98ebc760, d0a4ccb3646c79ad, bda1da8f5bc3b679, 363d53a23c23f150, 135c077a65b61dda, 6a2c44f62f58bd05, 0c557d74dd5dcc14, 19b2c00e70a40ab1, f07f7955a1ecbd39, 0ada5d894838d46e, dadedf10efb45ade]
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
customer-owned layer instead of a vendor dashboard. A managed vendor is now
meeting that self-hosted instinct partway: LangSmith's Bring Your Own Cloud
option reached general availability on AWS, giving an enterprise team
managed observability, evaluation, and deployment while the workload itself
stays inside their own VPC — the same "keep it in our network" requirement
the Claude Apps Gateway answers by self-hosting, here answered by a vendor
deploying its managed product into the customer's cloud instead.

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

A named experiment sharpens where the RCA bottleneck actually sits: a Coroot
test running root-cause analysis across eleven models finds LLMs can
already do the reasoning once given correctly prepared context, which
reframes the hard problem from "can the model reason about the failure" to
"can the pipeline correlate telemetry into that context" — the same
context-assembly work Expedia's STAR already invests in rather than a
bigger model. The self-hosted, indie tooling layer keeps growing alongside
the vendor consolidation this page tracks: a Show HN entrant ships
observability specifically for coding agents and LLM applications, one more
option in the trace-first tooling space beyond the named vendors above.

A new benchmark puts a number on how far that reasoning-vs-pipeline gap
still has to close: ORCA-bench pairs a live, OpenTelemetry-instrumented
microservice testbed (six days of metrics, logs, and traces through
Prometheus, Jaeger, and OpenSearch) with 1,079 oncall root-cause-analysis
tasks graded by an LLM-as-judge independently re-scored by human SREs
(agreement κ=0.90). Across five frontier agents the best RCA accuracy is
25.3% on realistic-input tasks and 10.0% on hard ones — a gap that holds
even for Claude Fable 5, and the weakest model hallucinates an implausible
root cause on 40% of reports. Since the testbed is a curated 50GB slice of a
public system, the authors read this as a lower bound on the real-world
gap, sharpening the Coroot finding above: the reasoning may already be
there, but the end-to-end oncall pipeline this page tracks (telemetry
correlation, ambiguous reports, time pressure) is still mostly unsolved.

A named production deployment pairs tracing with a human-approval gate
rather than auto-resolving: LangChain built an autonomous SRE agent for
Kubernetes on Deep Agents that requires human approval before it applies a
change, with every step, tool call, and decision captured in LangSmith
traces — an instance of the trace-first, agentic-analysis pattern above
(Expedia's STAR, HALO) where the trace is also what a human reviews before
the agent is allowed to act, not just what an engineer replays afterward.

Capture tooling itself is widening on the open-source side: Simon Willison's
`llm` CLI (0.32) adds support for visible reasoning traces and redesigned,
smarter logging alongside server-side provider tools — the same
trajectory-capture discipline the vendor platforms above ship, now available
in a widely-used, framework-agnostic command-line tool rather than only a
hosted product.

A major serving platform now ships tracing **natively** rather than leaving
it to a third-party SDK: Cloudflare added agent tracing directly into
existing Workers traces, with `invoke_agent` → `chat`/`execute_tool` →
`tool_approval` spans keyed by agent name, agent ID, and conversation ID so
a session replays turn by turn. The launch also exposes the privacy tension
this page's trace-first shift creates rather than solves: message and tool
payloads default to *not* being stored under one SDK wrapper (Vercel's AI
SDK) but *are* stored by default under another (Flue) — the same platform
feature ships with opposite privacy defaults depending on which harness a
team already picked, and those payloads routinely carry personal data or
secrets. Payloads are also subject to undisclosed span-size truncation, so a
trace can silently drop the reasoning or tool arguments a debugging session
needed most.

The trace-first thesis has a **boundary condition** when agents talk to each
other: work on Verifiable Latent Alignments (VLA) starts from the fact that
language-model agents can coordinate through continuous hidden states that
never appear in the public transcript, so a complete trace of what was *said*
can still miss what was *communicated*. VLA links each private latent-state
record and channel status to the resulting public action through a shared
event identifier, so a monitor can causally match a decision against the
hidden channel that produced it, and combines representation anomaly
detection into a layered monitor rather than reading transcripts alone. It
sharpens what "capture the full trajectory" has to mean in a multi-agent
system (see [multi-agent](/topic/multi-agent)): the span schema this page
tracks records messages and tool calls, and that is the wrong unit when the
coordination happens below the message layer.

## What's new
Latent-channel monitoring marks the first real limit on this page's
trace-first stance: agents can coordinate through hidden states invisible in
the public transcript, so message-and-tool-call spans are not a complete
record of a multi-agent run. VLA's answer is to link each private latent
record to the public action it caused via a shared event identifier — a
monitoring unit below the span, not a better span.

Prior update: Cloudflare shipped agent tracing natively into its existing Workers
traces, but the launch also surfaces a real gotcha: message/tool payload
storage defaults are opposite between its two supported SDKs (off by
default in one, on by default in the other), so the same platform feature
can silently retain or silently drop personal data depending on which
harness a team already chose.

Prior update: LangSmith's Bring Your Own Cloud option reached general availability on
AWS — managed observability, evaluation, and deployment with the workload
kept inside the customer's own VPC, meeting the self-hosted control-plane
pattern this page already tracks (AWS's Claude Apps Gateway) from the
vendor side rather than the customer-built side.

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
