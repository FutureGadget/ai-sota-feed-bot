---
slug: agent-orchestration
kind: solution
title: "Orchestration patterns: topologies, handoffs, and harnesses"
status: active
obstacles: [multi-agent]
related_storylines: []
evidence: [19e4caf222bfb0d9, e7f12e82187d72de, 64ad8e685ed41a9b, 296564a4c4e09d02, ba5ccf9069d7bcf3, 184459768c3c7f3a, 687049f045800948, f27164f724f79fa3, 21835f1d1d66cb1d, d1a43a5f27d69d48, 8e0e2c22560bbc7b]
updated: 2026-07-10
covers_evidence: [19e4caf222bfb0d9, e7f12e82187d72de, 64ad8e685ed41a9b, 296564a4c4e09d02, ba5ccf9069d7bcf3, 184459768c3c7f3a, 687049f045800948, f27164f724f79fa3, 21835f1d1d66cb1d, d1a43a5f27d69d48, 8e0e2c22560bbc7b]
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
decorrelated errors across models rather than picking one "best" agent.

## What's new
Code-driven orchestration goes **provider-agnostic**: Omegacode's JavaScript
DSL spawns Codex, Claude Code, OpenCode, or pi agents from the same workflow
script, shipping multi-provider patterns (adversarial review, bake-offs)
that exploit decorrelated errors across models — extending last round's
single-framework code-driven fan-out (LangChain dynamic subagents) to
heterogeneous agent fleets.

That lands alongside orchestration showing up as **shipping practitioner
tooling**, not just patterns:

- Multi-model routing inside a terminal coding agent (**Kimchi**)
- Visual sub-agent wiring for Claude Code (**rondoflow**)
- Transparency-first multi-agent runners (**OpenOrb**)

— all putting the engineering into the routing/handoff/wiring layer between
agents.

That sits on top of the framing of orchestration as a **runtime-substrate**
problem (workspace, runtime, and per-agent directory isolation as the
load-bearing design) and the move from "add more agents" to "design the
coordination" — decentralized topologies (DeLM) and per-task generated
harnesses (Anthropic) displacing the single-coordinator star.

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
