---
slug: agent-orchestration
kind: solution
title: "Orchestration patterns: topologies, handoffs, and harnesses"
status: active
obstacles: [multi-agent]
related_storylines: []
evidence: []
updated: 2026-11-28
themes:
  - key: code-driven
    title: Coordination written as code, not tool calls
    summary: Harnesses now drive sub-agent fan-out from programs, generated per task or written in plain JavaScript or Python, so coverage comes from control flow and one script can mix agents from different providers.
  - key: orchestrator-tooling
    title: Open-source orchestrators and multi-model routers
    summary: A wave of open-source and vendor orchestrators routes steps across models and makes sub-agent wiring visible; most are early, but they put the value in the routing and handoff layer, not the agents.
  - key: runtime-substrate
    title: The durable runtime underneath the agents
    summary: Workspace layout, durable queues, leases, and checkpoints are the load-bearing parts; options range from a Postgres recipe to purpose-built kernels and Google's Kubernetes-style AX.
  - key: harness-choice
    title: "Choosing a harness: frameworks, managed runtimes, portability"
    summary: Microsoft, LangChain, and OpenAI now sell harnesses as managed runtimes, while practitioner guides and AWS argue for matching the framework to the workflow and keeping a multi-vendor estate portable.
---

## TL;DR
Orchestration is the control plane of a multi-agent system: how the work is
decomposed, which agent does what, how they hand off, and who — if anyone — is
in charge. The pattern you pick (central orchestrator vs. decentralized, a fixed
graph vs. one generated per task) sets the cost, latency, and reliability
ceiling of the whole system.

## State of the art
Orchestration is converging on **coordination written as code**. Harnesses
drive fan-out from a program (Deep Agents' dynamic subagents), generate a
harness per task, or let a plain script spawn Claude Code, Codex, and other
agents side by side. Control flow becomes deterministic, testable code around
non-deterministic agents.

**The harness can matter more than the model.** Swapping the harness moved
one open-weight model from 30% to 81% task completion, and on small local
models the harness decides whether a run produces anything at all. Hugging
Face now trains RL adapters that tune a model to one harness.

**Topology is a cost decision.** A central orchestrator is easy to trace but
is a bottleneck; removing it cut task cost about 50% in one study. The value
sits in the interface contracts between agents, and schema-valid output still
does not mean task-correct output.

**The runtime substrate is load-bearing.** Where each sub-agent runs, what
state it sees, and how work survives a crash decide reliability. Options span
a Postgres recipe (`SKIP LOCKED` dispatch, checkpoints, leases), queues with
dead-letter states, and coordinators that compile a workflow into an
immutable plan. Recovery is getting finer: re-running only a failed node's
descendants recovered every task in one benchmark versus 55% for
whole-trajectory replay.

**Harnesses are becoming managed platforms.** Microsoft's Agent Framework and
Foundry Hosted Agents are GA, LangChain's Managed Deep Agents is in beta, and
OpenAI sells the Codex harness as a service. Large internal platforms such as
iFood's turn repo chores across 15,000 repositories into API calls.

The open question is which layer to own. Managed runtimes remove the plumbing
but tie durable state, memory, and evals to one vendor. Code-driven,
provider-agnostic orchestration keeps you portable at the cost of running the
substrate yourself.

## Trade-offs
A central orchestrator is easy to trace and debug but caps throughput and adds a
bottleneck; decentralized topologies scale and cut cost but are harder to observe
and can deadlock or diverge. Generated orchestration adapts per task but is less
predictable and harder to test than a fixed graph. More agents and more
coordination nearly always cost more tokens and latency, so the pattern only
pays off when the task genuinely decomposes and the handoffs are cheap and
well-typed — otherwise the orchestration overhead is pure loss.

A managed runtime removes the queue, checkpoint, and sandbox plumbing but
couples durable state and evals to one vendor's platform.

## Why it matters for platform engineers
This is distributed-systems design wearing an LLM hat: topology choice,
backpressure, handoff schemas, and failure isolation. The actionable stance is
to default to a single agent, reach for orchestration only when a task
decomposes cleanly, prefer decentralized or contract-based handoffs over a fat
central coordinator where you can trace them, and measure (see
[agent benchmarks](/topic/agent-benchmarks)) that the multi-agent version
actually beats the single-agent baseline on cost and reliability before you ship
it.
