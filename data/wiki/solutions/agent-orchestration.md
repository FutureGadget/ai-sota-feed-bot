---
slug: agent-orchestration
kind: solution
title: "Orchestration patterns: topologies, handoffs, and harnesses"
status: active
obstacles: [multi-agent]
related_storylines: []
evidence: [19e4caf222bfb0d9, e7f12e82187d72de, 64ad8e685ed41a9b]
updated: 2026-06-19
covers_evidence: [19e4caf222bfb0d9, e7f12e82187d72de, 64ad8e685ed41a9b]
---

## TL;DR
Orchestration is the control plane of a multi-agent system: how the work is
decomposed, which agent does what, how they hand off, and who — if anyone — is
in charge. The pattern you pick (central orchestrator vs. decentralized, a fixed
graph vs. one generated per task) sets the cost, latency, and reliability
ceiling of the whole system.

## State of the art
Two axes are in play. **Topology**: the orchestrator-worker (star) pattern is
the simplest to reason about but makes the coordinator a throughput bottleneck
and a single point of failure — Stanford's DeLM reports cutting task cost ~50%
by removing the central orchestrator, and DPBench finds the communication
structure is the dominant determinant of whether coordination helps at all.
**Dynamism**: orchestration is moving from hand-wired graphs toward *generated*
control flow — Anthropic's Claude Code Dynamic Workflows generate a custom
execution harness per task to coordinate sub-agents rather than committing to one
static shape. Across both axes the durable lesson is that the value lives in the
**interface contracts** between agents — structured handoffs, compact wire
formats, explicit roles — not in the number of agents you spin up.

## What's new
The center of gravity has moved from "add more agents" to "design the
coordination": decentralized topologies that drop the central orchestrator (DeLM)
and per-task generated harnesses (Anthropic) are displacing the default
single-coordinator star, with the communication structure treated as the primary
design variable.

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
