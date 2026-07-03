---
slug: multi-agent
kind: obstacle
title: "Coordinating multiple agents adds more failure than capability"
area: multi-agent
status: active
solutions: [agent-orchestration, agent-benchmarks]
obstacles: []
related_storylines: []
evidence: [64ad8e685ed41a9b, 19e4caf222bfb0d9, e7f12e82187d72de, f961ee6418699914, 884659da8630c702, 296564a4c4e09d02, ba5ccf9069d7bcf3, 184459768c3c7f3a, 687049f045800948, f27164f724f79fa3, e42bb42a72fb81a4, 8875da5519a24b6e]
updated: 2026-07-03
covers_evidence: [64ad8e685ed41a9b, 19e4caf222bfb0d9, e7f12e82187d72de, f961ee6418699914, 884659da8630c702, 296564a4c4e09d02, ba5ccf9069d7bcf3, 184459768c3c7f3a, 687049f045800948, f27164f724f79fa3, e42bb42a72fb81a4, 8875da5519a24b6e]
---

## TL;DR
Splitting a job across several agents promises specialization and parallelism,
but every handoff is a lossy interface and each added agent multiplies the ways
the system can stall, loop, or disagree. Coordination overhead routinely eats
the gains — the hard part isn't building the agents, it's getting them to work
together without costing more than one good agent would.

## State of the art
The conversation is shifting from "more agents is better" to characterizing
*when* multi-agent actually helps, and the recurring answer is that the
**communication structure dominates the agent count**. DPBench studies the
structural determinants of multi-agent LLM coordination directly — which
topologies and role assignments make collaboration pay off versus add noise.

**Cost** is the second axis: Stanford's DeLM reports cutting multi-agent task
cost by roughly half by *removing the central orchestrator*, evidence that a
single coordinating agent is both a token bottleneck and a single point of
failure.

Orchestration itself is becoming **dynamic** rather than hand-wired —
Anthropic's writeup on Claude Code's Dynamic Workflows describes generating a
custom execution harness per task to coordinate sub-agents instead of
committing to one fixed shape. The sharper version of that move is
orchestrating sub-agents **with code rather than tool calls**: LangChain's
dynamic subagents in Deep Agents drive fan-out and coordination from a
program, so coverage is *guaranteed* by control flow instead of hoped-for
from the model emitting one tool call per worker — turning the coordination
layer into ordinary (testable, deterministic) code around non-deterministic
agents.

The flip side of caring about communication structure is that the structure
is also an **attack surface**: the "Linguistic Firewall" work treats routing
in a multi-agent system as a geometry problem and defends it, because a
compromised or adversarial agent in the mesh can steer the others — so
robust handoffs are a security property, not just a quality one.

Meanwhile practitioners are still hunting for frameworks where
*heterogeneous* models genuinely collaborate (route refactors to one model,
codegen to another), which is really a routing-and-handoff problem, not a
model problem — and that hunt is now materializing as shipping tooling:

- Coding agents with built-in multi-model orchestration (**Kimchi** routes a terminal coding agent across models)
- Visual orchestration UIs that let you wire sub-agents by hand for Claude Code (**rondoflow**)
- Transparency-first multi-agent tools (**OpenOrb**) that surface what each agent did

The common thread is that the hard, load-bearing work has moved out of the
agents and into the *routing, wiring, and visibility* layer between them.

A sharper version of the "is it worth it" question is now visible at both
ends: Sakana's Fugu *collapses* a multi-agent system into a single distilled
model — trading the coordination layer away entirely once the division of
labor is known — while practitioners building orchestration libraries report
that the real engineering is mundane plumbing (workspaces, runtimes,
directory layout for sub-agents) rather than clever agent roles.

The durable lesson: who talks to whom, in what format, and under whose
control is the dominant variable — and sometimes the cheapest topology is no
topology at all.

A newer thread ties coordination quality directly to **uncertainty**: UA-ChatDev
has role-based software-development agents track and act on their own
confidence, so a low-confidence step triggers deliberation or hand-off rather
than confidently propagating a mistake to the next role — coordination
reliability as a function of agents knowing what they don't know, not just of
topology.

## What's new
Coordination reliability gets an **uncertainty-aware** treatment: UA-ChatDev
has role-based agents track confidence and use it to trigger deliberation
before a shaky step gets handed to the next agent, addressing the
handoff-propagates-mistakes failure mode from inside the agents rather than
from the routing layer around them — a complement to last round's
**code-driven orchestration** shift (LangChain's dynamic subagents
guaranteeing fan-out coverage via control flow) and the **security** framing
of routing as an attack surface (Linguistic Firewall).

## Why it matters for platform engineers
Every extra agent is extra tokens, extra latency, and extra failure surface, so
a multi-agent design has to clear a hard bar: beat a single well-prompted agent
on cost *and* reliability — and it often doesn't. The engineering job is
choosing a topology (orchestrator-worker vs. decentralized), writing strict
handoff contracts so one agent's output is safely another's input, and budgeting
the communication overhead up front. Crucially it needs an eval (see
[agent benchmarks](/topic/agent-benchmarks)) that proves the extra agents paid
for themselves, because the default failure mode is paying N× the cost for a
result a single agent could have produced.
