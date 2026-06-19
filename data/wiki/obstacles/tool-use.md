---
slug: tool-use
kind: obstacle
title: "Agents reach the outside world through fragile, ad-hoc integrations"
area: tool-use
status: active
solutions: [mcp]
obstacles: []
related_storylines: []
evidence: [6d71486170022687, 8bad13df6e63105d, 0652695d185d0b1f, 5b5273180a38e7c0]
updated: 2026-06-19
covers_evidence: [6d71486170022687, 8bad13df6e63105d, 0652695d185d0b1f, 5b5273180a38e7c0]
---

## TL;DR
An agent is only as useful as the tools it can call, but every integration has
historically been bespoke: hand-written wrappers around REST APIs, brittle
schemas the model misuses, and no shared way to discover or authorize tools.
Connecting an agent to real systems — infra, browsers, SaaS — is where a lot of
the engineering actually goes, and it breaks in production in ways the model
never sees.

## State of the art
The field is converging on a **protocol layer** rather than per-app glue: the
Model Context Protocol (MCP) standardizes how tools are described, discovered,
and called, so a Terraform server, a Webex server, or a browser can expose
capabilities to any MCP-speaking agent. The argument has sharpened from "wrap
your REST API" to "agents need *infrastructure*, not SMS APIs" — purpose-built,
agent-native endpoints rather than human-oriented ones bolted on. The actuation
surface is widening too: WebMCP is entering Chrome origin trials so sites can
expose JavaScript functions and HTML forms directly to in-browser agents.
Running this in production surfaces classic distributed-systems problems —
bursty, stateful multi-tenancy and securing the execution sandbox — that the
model's tool-calling ability does nothing to solve.

## What's new
Tool use is standardizing fast: WebMCP moving into Chrome origin trials (in-page
tools for browser agents) and the GA of infrastructure MCP servers like
HashiCorp's Terraform server mark the shift from one-off integrations to a
shared, discoverable protocol surface.

## Why it matters for platform engineers
Tool integration is the part of an agent that looks like ordinary distributed
systems — auth, rate limits, retries, multi-tenancy, sandboxing — and it is
where most production incidents live, not in the model. A protocol like MCP
reduces N×M custom connectors to a common interface, but it also makes the
**authorization and blast-radius** question central: every tool you expose is a
new permission and a new attack surface (see [prompt injection](/topic/prompt-injection)).
The build-vs-buy decision is increasingly "adopt the protocol and govern the
connectors" rather than "write another API wrapper."
