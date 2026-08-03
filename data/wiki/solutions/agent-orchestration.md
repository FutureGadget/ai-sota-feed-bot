---
slug: agent-orchestration
kind: solution
title: "Orchestration patterns: topologies, handoffs, and harnesses"
status: active
obstacles: [multi-agent]
related_storylines: []
evidence: [19e4caf222bfb0d9, e7f12e82187d72de, 64ad8e685ed41a9b, 296564a4c4e09d02, ba5ccf9069d7bcf3, 184459768c3c7f3a, 687049f045800948, f27164f724f79fa3, 21835f1d1d66cb1d, d1a43a5f27d69d48, 8e0e2c22560bbc7b, 4d5ebc5e9dfb5949, 012864be2b78cf49, e6a4bc0259ec51da, 675fc28b9b02c667, 8fb08df9d34b4a09, f5869c6c9f8fd679, 7f65b3c679e761ab]
updated: 2026-08-03
covers_evidence: [19e4caf222bfb0d9, e7f12e82187d72de, 64ad8e685ed41a9b, 296564a4c4e09d02, ba5ccf9069d7bcf3, 184459768c3c7f3a, 687049f045800948, f27164f724f79fa3, 21835f1d1d66cb1d, d1a43a5f27d69d48, 8e0e2c22560bbc7b, 4d5ebc5e9dfb5949, 012864be2b78cf49, e6a4bc0259ec51da, 675fc28b9b02c667, 8fb08df9d34b4a09, f5869c6c9f8fd679, 7f65b3c679e761ab]
---

## TL;DR
Orchestration is the control plane of a multi-agent system: how the work is
decomposed, which agent does what, how they hand off, and who — if anyone — is
in charge. The pattern you pick (central orchestrator vs. decentralized, a fixed
graph vs. one generated per task) sets the cost, latency, and reliability
ceiling of the whole system.

## State of the art
Two axes are in play.

**Topology**: the orchestrator-worker (star) pattern is the simplest to
reason about but makes the coordinator a throughput bottleneck and a single
point of failure — Stanford's DeLM reports cutting task cost ~50% by
removing the central orchestrator, and DPBench finds the communication
structure is the dominant determinant of whether coordination helps at all.

**Dynamism**: orchestration is moving from hand-wired graphs toward
*generated* control flow — Anthropic's Claude Code Dynamic Workflows
generate a custom execution harness per task to coordinate sub-agents rather
than committing to one static shape. More concretely, it's moving toward
orchestrating sub-agents **in code rather than tool calls**: LangChain's
dynamic subagents in Deep Agents drive fan-out from a program so coverage is
guaranteed by control flow instead of by the model emitting one tool call
per worker, making the coordination layer ordinary deterministic, testable
code wrapped around non-deterministic agents.

Across both axes the durable lesson is that the value lives in the
**interface contracts** between agents — structured handoffs, compact wire
formats, explicit roles — not in the number of agents you spin up.

A third, quieter axis is the **runtime substrate**: writeups from teams
building orchestration libraries report that the load-bearing design is
workspace, runtime, and directory layout — where each sub-agent runs, what
filesystem and state it sees, how outputs are isolated and collected — i.e.
orchestration is as much an execution-environment problem as a
control-flow one.

A fourth axis is now appearing as **shipping tooling rather than research**:
practitioner orchestrators that make the wiring tangible —

- Multi-model routing built into a terminal coding agent (**Kimchi**, sending refactors and codegen to different models)
- Visual sub-agent wiring for Claude Code (**rondoflow**)
- Transparency-first multi-agent runners that expose each agent's actions (**OpenOrb**)

They are early and uneven, but they confirm where the value sits: the
routing, handoff, and observability layer between agents, not the agents
themselves.

A fifth axis makes the code-driven pattern **provider-agnostic**: Omegacode
composes `agent()`/`parallel()`/`pipeline()`/`phase()` in a plain JavaScript
DSL, and any `agent()` call can spawn a Codex, Claude Code, OpenCode, or pi
agent — the same workflow script mixing providers instead of one script per
framework. Its built-in patterns (adversarial code review, model bake-offs)
treat the provider mix itself as the design lever, deliberately using
decorrelated errors across models rather than picking one "best" agent. The
same provider-agnostic pattern is landing in Python, not just JavaScript:
h5i-python defines and executes multi-agent coding workflows across Claude
Code, Codex, and other runtimes as ordinary Python programs, confirming the
pattern is a language-agnostic design choice rather than one DSL's idea.

A sixth axis names the **conflict-resolution** gap directly: an arbiter role
resolves disagreement between a planning agent and a coding agent by
checking the code against the plan rather than trusting either agent's own
report, packaged with per-role credentials and human-readable communication
into a governance layer — a concrete answer to "who's in charge when two
agents disagree," distinct from the topology question of who talks to whom.
Low-code platforms are also folding orchestration and the agent loop into
one engine rather than two layers: one open-source platform embeds a full
model-call/tool-call/observation loop as a drag-and-drop workflow step,
sharing an audit trail across agent decisions, tool calls, and workflow
steps alike.

A seventh axis supplies **field-tested recipes at the framework level**: a
LangGraph practitioner guide positions the framework by workflow-complexity
fit — typed state, conditional routing, deterministic tools, retries,
interrupts, checkpoints, and traces earn their keep on long-running stateful
processes (SQL analytics with repair loops, evidence-gated RAG,
human-in-the-loop policy review) — but recommends simpler ReAct-style loops,
schema-first tools, or DSPy when the job doesn't need that structure. A
production deployment backs the same "orchestration pays for itself when the
task is real" argument with numbers: a live 5G-core security-operations
center's A2A+MCP multi-agent architecture cut mean time to detect/respond
40% and human review load 12x.

An eighth axis is the orchestration SDK itself showing up by name in
production deployments outside that one showcase: Jefferies, an investment
bank, built a front-office trading assistant on Strands Agents — an open
agent-harness SDK for building agents that reason, plan, and act by
orchestrating calls to foundation models and tools — paired with Amazon
Bedrock, Amazon Bedrock Knowledge Bases, and MCP for unified access to
trading data sources and tools. Apollo's GTM AI Assistant orchestrates a
different harness, "Deep Agents," with LangSmith and its own MCP
integrations, across prospecting, enrichment, outreach, and analytics. Two
distinct harnesses reaching production in two distinct industries (finance,
sales/GTM) rather than one orchestration framework winning outright.

A ninth axis adds a fourth named deployment on the checkpoint-and-recovery
side of harness choice: an AWS reference architecture for market
surveillance orchestrates LangGraph for workflow control and Strands for
agent reasoning on Amazon Bedrock AgentCore, using checkpoint-based recovery
plus AgentCore's built-in memory and observability instead of hand-rolling
either — a fourth harness/platform combination in production alongside
Strands+Bedrock (Jefferies) and Deep Agents+LangSmith (Apollo).

A tenth axis is a framework vendor making the same SDK-to-platform jump
from the provider side rather than the enterprise-adopter side: Microsoft's
Agent Framework — the Agent Harness, GitHub Copilot and Claude Agent SDK
connectors, and its orchestration patterns, all stable since Build 2026 —
now ships the harness and Foundry Hosted Agents at general availability, a
supported runtime rather than an SDK you assemble yourself. It's the same
shift the Strands and LangGraph deployments above make by adoption; here
the framework itself reaches that bar.

## What's new
Microsoft's Agent Framework crossed from SDK to supported infrastructure:
the Agent Harness, GitHub Copilot and Claude Agent SDK connectors, and its
orchestration patterns — stable since Build 2026 — now ship as a governed
platform, with the harness and Foundry Hosted Agents reaching general
availability rather than staying a build-it-yourself SDK.

## Trade-offs
A central orchestrator is easy to trace and debug but caps throughput and adds a
bottleneck; decentralized topologies scale and cut cost but are harder to observe
and can deadlock or diverge. Generated orchestration adapts per task but is less
predictable and harder to test than a fixed graph. More agents and more
coordination nearly always cost more tokens and latency, so the pattern only
pays off when the task genuinely decomposes and the handoffs are cheap and
well-typed — otherwise the orchestration overhead is pure loss.

## Why it matters for platform engineers
This is distributed-systems design wearing an LLM hat: topology choice,
backpressure, handoff schemas, and failure isolation. The actionable stance is
to default to a single agent, reach for orchestration only when a task
decomposes cleanly, prefer decentralized or contract-based handoffs over a fat
central coordinator where you can trace them, and measure (see
[agent benchmarks](/topic/agent-benchmarks)) that the multi-agent version
actually beats the single-agent baseline on cost and reliability before you ship
it.
