---
slug: tool-use
kind: obstacle
title: "Agents reach the outside world through fragile, ad-hoc integrations"
area: tool-use
status: active
solutions: [mcp]
obstacles: []
related_storylines: []
evidence: [6d71486170022687, 8bad13df6e63105d, 0652695d185d0b1f, 5b5273180a38e7c0, 4f7d4f99793e131d, ebc3627096b332c8, d0a3b1456466205e, d6f47c6e7ea5d37c, cf37950940d3d2b5, 2e309060a5831bee, 3c227e4c9b2cd2eb]
updated: 2026-07-10
covers_evidence: [6d71486170022687, 8bad13df6e63105d, 0652695d185d0b1f, 5b5273180a38e7c0, 4f7d4f99793e131d, ebc3627096b332c8, d0a3b1456466205e, d6f47c6e7ea5d37c, cf37950940d3d2b5, 2e309060a5831bee, 3c227e4c9b2cd2eb]
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
agent-native endpoints rather than human-oriented ones bolted on.

But most enterprises can't rebuild their service estate agent-native, so a
pragmatic **brownfield** pattern is emerging alongside the greenfield one:
agentic overlays — thin wrapper layers (AWS) that sit in front of existing
REST services and expose them as agent-callable capabilities without touching
the underlying system, trading the purity of agent-native endpoints for
adopting what already runs in production.

The **actuation surface** is widening too: WebMCP is entering Chrome origin
trials so sites can expose JavaScript functions and HTML forms directly to
in-browser agents, and cloud platforms are folding the whole tool-calling loop
into their serverless runtimes — Azure Functions' agents runtime defines an
agent in an `.agent.md` file with YAML triggers, MCP server access, 1,400+
connectors, and sandboxed execution. Running this in production surfaces
classic distributed-systems problems — bursty, stateful multi-tenancy and
securing the execution sandbox — that the model's tool-calling ability does
nothing to solve.

Standardizing the *wire* does not make the *calling behavior* reliable, and
that is emerging as a separate, measurable failure axis. "Beyond Function
Calling" benchmarks agents against **tool-environment unreliability** — tools
that time out, error, or return malformed or inconsistent results — and finds
that agents which look competent on clean tool suites degrade sharply when
the environment misbehaves, so a passing schema test is no evidence the agent
recovers when the tool itself does.

A second, sharper finding is an *interaction* bug in the harness: the
**"Constraint Tax"** study shows that demanding structured (JSON-schema)
output and tool calling jointly suppresses tool calling in open-weight
models — the two core agent capabilities interfere, so forcing a clean output
contract can quietly stop the agent from calling the tool it needed.

A third axis is **tool selection at scale**: once an agent can reach dozens
of connectors, putting every tool schema in the prompt both burns context
budget and degrades which tool the model picks, so harnesses are moving to
*search* the tool catalog instead of listing it — OpenAI's Codex now uses
[MCP](/topic/mcp) tool search by default, turning tool discovery into a
retrieval step rather than a context dump.

A fourth axis is **tool definition quality itself**, now a named discipline
rather than an afterthought: a field guide catalogs concrete anti-patterns —
always-loaded bloated schemas, vague internal-naming, oversized result
payloads — and a fix progression through richer descriptions, typed
constraints, and lazy-loaded discovery that cut per-turn context usage in
half in one case study (see [MCP](/topic/mcp) for the full progression).
Governance is maturing alongside design: the protocol's own
Enterprise-Managed Authorization extension reached stable status, replacing
per-server consent prompts with a single sign-on flow through an
organization's identity provider — standardizing what individual vendors had
already shipped one-off.

## What's new
Tool **definition quality** joins tool selection as a named engineering
discipline: a field guide catalogs concrete schema anti-patterns and a fix
progression (richer descriptions, typed constraints, lazy-loaded discovery)
that roughly halved per-turn context usage in one case study. Governance
matured alongside it: MCP's Enterprise-Managed Authorization extension
reached stable status, standardizing single-sign-on connector auth across
any MCP client or server rather than leaving it to individual vendors.

## Why it matters for platform engineers
Tool integration is the part of an agent that looks like ordinary distributed
systems — auth, rate limits, retries, multi-tenancy, sandboxing — and it is
where most production incidents live, not in the model.

A protocol like MCP reduces N×M custom connectors to a common interface, but
it also makes the **authorization and blast-radius** question central: every
tool you expose is a new permission and a new attack surface (see
[prompt injection](/topic/prompt-injection)).

The build-vs-buy decision is increasingly "adopt the protocol and govern the
connectors" rather than "write another API wrapper."
