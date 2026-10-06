---
slug: tool-use
kind: obstacle
title: "Agents reach the outside world through fragile, ad-hoc integrations"
area: tool-use
status: active
solutions: [mcp]
obstacles: []
related_storylines: []
evidence: []
updated: 2026-10-06
themes:
  - key: agent-native-surfaces
    title: Exposing existing systems as agent-callable tools
    summary: Teams either build agent-native endpoints or wrap what already runs, via thin overlays, generated MCP surfaces, or per-app capabilities; wrapping is winning in the enterprise.
  - key: discovery-and-definitions
    title: Tool discovery and definition quality at scale
    summary: Listing every schema in the prompt burns context and hurts tool choice, so harnesses now search the tool catalog and teams treat tool definitions as a design discipline.
  - key: calling-reliability
    title: Making the calling loop reliable
    summary: A standard wire does not make calling behavior reliable; flaky tools, schema-constraint interference, and connection failures are measurable failure modes, and the harness itself is now tuned or trained to fix them.
  - key: guarding-the-call
    title: Checking and governing tool calls before they run
    summary: Controls are moving from scoping what a tool can touch to checking each call before execution and writing policy over sequences of calls, at the cost of stateful tracking.
  - key: production-runtimes
    title: Running tool-calling agents in production
    summary: Cloud runtimes now host the tool loop, and production deployments narrow the model to orchestration while specialized components, approvals, and isolation carry the work.
---

## TL;DR
An agent is only as useful as the tools it can call, but every integration has
historically been bespoke: hand-written wrappers around REST APIs, brittle
schemas the model misuses, and no shared way to discover or authorize tools.
Connecting an agent to real systems is where much of the engineering goes, and
it breaks in production in ways the model never sees.

## State of the art
**The wire is standardizing on a protocol layer.** [MCP](/topic/mcp) describes,
discovers, and calls tools the same way for every agent, so the per-app glue
question is mostly settled. Enterprises reach it two ways: purpose-built
agent-native endpoints, or (more often) thin overlays and generated MCP
surfaces in front of services that already run.

**Discovery is now a retrieval problem.** Once an agent can reach dozens of
connectors, loading every schema burns context and degrades tool choice.
Harnesses now search the tool catalog by default and keep intermediate results
out of the model's context. Vendor numbers show this lifts accuracy, not only
token budgets. Tool definitions (names, typed constraints, example inputs,
result size) are treated as a design discipline.

**Calling behavior is the open problem.** Agents that pass clean tool suites
degrade when tools time out or return bad data, and enabling JSON-schema output
alongside tool calling can stop open-weight models from calling tools at all.
The response is to tune or train the harness around the tools: search over
harness configurations with frozen weights, or record harness rollouts as RL
data.

**Governance is moving earlier in the call.** Beyond who may connect, teams now
verify a proposed call before it runs and write policy over sequences of calls,
since per-request checks miss concurrent abuse. Temporal policies need stateful
tracking and give up some formal guarantees.

Production deployments keep the model's job narrow: orchestration and
language, with specialized components, approvals, and isolated execution doing
the rest.

## Why it matters for platform engineers
Tool integration is the part of an agent that looks like ordinary distributed
systems: auth, rate limits, retries, multi-tenancy, sandboxing. That is where
most production incidents live, not in the model.

A protocol like MCP reduces N×M custom connectors to one interface, but it
makes **authorization and blast radius** central: every exposed tool is a new
permission and a new attack surface (see
[prompt injection](/topic/prompt-injection) and
[agent sandboxing](/topic/agent-sandboxing)).

The build-vs-buy decision is now "adopt the protocol and govern the
connectors", plus testing how the agent behaves when a tool fails, rather than
"write another API wrapper".
