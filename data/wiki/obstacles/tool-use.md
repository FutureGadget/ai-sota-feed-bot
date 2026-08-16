---
slug: tool-use
kind: obstacle
title: "Agents reach the outside world through fragile, ad-hoc integrations"
area: tool-use
status: active
solutions: [mcp]
obstacles: []
related_storylines: []
evidence: [6d71486170022687, 8bad13df6e63105d, 0652695d185d0b1f, 5b5273180a38e7c0, 4f7d4f99793e131d, ebc3627096b332c8, d0a3b1456466205e, d6f47c6e7ea5d37c, cf37950940d3d2b5, 2e309060a5831bee, 3c227e4c9b2cd2eb, d4d5677e2459e3ab, 3f88ef2405b8fae7, 916521ba0baad7c0, 7a982846f4848d96, eec5c9b0fcd373da, 2e3ad0e505f55b80, b734d716b0d66f96, 9352c956aa90126f, ea850b1a9c912609, 793d1e28a9d4d499, 4daf9a3fc6b23a4c, cfcd5af1b5266bac, 801edb72737f6642, 410ca031ddd240de]
updated: 2026-08-16
covers_evidence: [6d71486170022687, 8bad13df6e63105d, 0652695d185d0b1f, 5b5273180a38e7c0, 4f7d4f99793e131d, ebc3627096b332c8, d0a3b1456466205e, d6f47c6e7ea5d37c, cf37950940d3d2b5, 2e309060a5831bee, 3c227e4c9b2cd2eb, d4d5677e2459e3ab, 3f88ef2405b8fae7, 916521ba0baad7c0, 7a982846f4848d96, eec5c9b0fcd373da, 2e3ad0e505f55b80, b734d716b0d66f96, 9352c956aa90126f, ea850b1a9c912609, 793d1e28a9d4d499, 4daf9a3fc6b23a4c, cfcd5af1b5266bac, 801edb72737f6642, 410ca031ddd240de]
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
agent-native endpoints rather than human-oriented ones bolted on. That
argument now reaches past data and API access into deterministic computation
itself: Euclid-MCP exposes SWI-Prolog logical reasoning behind a standard MCP
tool interface, with an engine-agnostic intermediate representation
(Euclid-IR) that an LLM can generate and the server compiles to Prolog through
a translate-run-inspect-repair loop — on a compliance-sensitive IT security
benchmark, LLMs alone hallucinate systematically as the knowledge base grows
while Euclid-MCP returns exact answers with lower latency and more compact
output (see [MCP](/topic/mcp)).

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
nothing to solve. A second browser vendor is now shipping the same surface:
Cloudflare previewed automatic WebMCP support that any site can turn on from
a dashboard switch, no code change required, letting browser-based agents
interact with an unmodified web page — widening WebMCP from a Chrome origin
trial one team opts into, to a one-click toggle a site operator flips.

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
already shipped one-off. That maturation reached a bigger milestone with the
**MCP 2026-07-28 spec**, the protocol's largest revision since launch:
stateless by default, a governed extensions system, and hardened
authorization — AWS's AgentCore Gateway already supports it, and InfoQ
published a defense-in-depth production-security architecture (safe
execution, management infrastructure, outbound calls, gateway) alongside it
(see [MCP](/topic/mcp) for the full spec and security detail). That statelessness
move has a live developer counter-argument, not just adoption: dropping the
initialize handshake and session header, and routing traffic on required
method and tool-name headers instead, reads to some practitioners as MCP
converging back toward "just an API" — the durable value the protocol still
adds over a plain REST call is the shared tool-description and discovery
layer this page already tracks, not the stateful session the spec just
removed. A practitioner variant of that governance push
pitches an intermediate protocol layer that turns raw APIs into versioned,
encapsulated "virtual tools" — interface mapping, dynamic schema projection,
and runtime taint tracking to catch data-exfiltration risk at the tool
boundary before it happens. This is one engineering leader's architecture
(Jake Mannix), not a benchmarked result, but it names the same gap the field
guide above targets: ungoverned tool sprawl, approached from versioning and
data-flow tracking rather than schema hygiene alone.

A fifth axis is **how much of the job the model should own at all**:
DoorDash's Ask DoorDash shopping assistant is a production counter-example to
routing every capability through the LLM, splitting the work across
specialized agents, [MCP](/topic/mcp)-based tooling, and a separate
persistent-memory intelligence layer rather than one model deciding
everything — narrowing the LLM's role to orchestration and language while
deterministic and specialized components carry the rest of the task.

A sixth axis is **hardening the tool call itself against injected content**:
Claude Code 2.1.210 patched its Agent tool specifically against indirect
prompt injection carried through content a subagent reads — a concrete,
shipped mitigation at the tool-call boundary rather than only a policy
argument for scoping what a tool is allowed to touch (see
[prompt injection](/topic/prompt-injection)).

A seventh axis is **the harness itself becoming the training bottleneck**:
the same elaborate multi-turn harnesses that make tool-calling agents
powerful — Claude Code, Codex, OpenClaw-style loops — are stateful,
multi-process systems that open SFT/RL stacks can't natively express, so
training a harness-native agent end-to-end has been out of reach for open RL
infrastructure. OpenForgeRL answers with a lightweight proxy that intercepts
a harness's model calls and records them as RL training data (e.g. for
veRL), paired with a Kubernetes orchestrator that runs each rollout in its
own remote container — validated across tool/harness-based agents and
multimodal GUI/browser-use agents, outperforming open baselines of similar
size on nearly every benchmark tested (ClawEval, QwenClawBench,
OSWorld-Verified, Online-Mind2Web, WebVoyager).

An eighth axis is **verifying the call itself before it runs**, distinct
from hardening against injected content: a static verifier for OpenCode
plugs formal-verification research ("Guardians of the Agents") into the
harness as a plugin, checking a proposed tool call against safety
properties before execution rather than only sandboxing or scoping what
happens after — a proactive, pre-execution check to sit alongside the
sandboxing and authorization controls tracked on
[agent sandboxing](/topic/agent-sandboxing).

A ninth axis is **reaching tools that were never meant to be reachable
remotely**: AWS built a secure MCP bridge so a cloud-hosted Bedrock
AgentCore agent can call MCP servers running on a user's own laptop,
tunneling signed messages over an existing WebSocket connection through a
browser extension rather than opening inbound ports or requiring a VPN — the
reverse of the usual "agent reaches a cloud API" direction, solved with the
same protocol rather than a bespoke remote-access tool (see [MCP](/topic/mcp)).

A tenth axis is **governing tool access at the platform layer**, alongside
the protocol's own auth extensions: Azure API Management shipped a
dedicated AI Gateway tier whose control plane is built around models, MCP
servers, and tools rather than APIs, fronting Foundry, Bedrock, Vertex AI,
and OpenAI behind one policy surface — a second cloud vendor (after AWS's
Claude Apps Gateway on the observability page) putting model *and* tool
governance behind a managed gateway instead of leaving it to per-connector
configuration (see [MCP](/topic/mcp)).

An eleventh axis is **governing the sequence of tool calls, not just one
call in isolation**: AWS open-sourced Dogwood, a policy language extending
its Cedar engine with temporal operators (`formerly`, `count_within`,
`count_distinct_within`, `sum_within`) that can read an agent's own
tool-call history rather than judging each request alone. The concrete case
for why this matters: a Cedar rule capping transfers at $5,000 that checks
*responses* is defeated by concurrency — three simultaneous $2,000 requests
all pass, because none has settled before the others arrive — so the rule
has to reason over *requests* within a time window instead. The trade-off is
real: temporal evaluation needs stateful event tracking and gives up Cedar's
automated formal-reasoning guarantees, a cost this page's authorization and
governance axes above (Enterprise-Managed Authorization, Azure's AI Gateway)
have not had to pay.

## What's new
AWS open-sourced Dogwood, a Cedar extension with temporal policy operators
that reason over an agent's tool-call *history* rather than one request at a
time — closing a concrete gap plain per-request authorization has: a
response-checked rate limit that three concurrent requests can defeat before
any of them settles.

Prior update: Cloudflare previewed automatic WebMCP support — any site can turn it on from
a dashboard toggle, no code change — widening the browser actuation surface
from a Chrome origin trial one team opts into to a one-click switch a site
operator flips. Separately, the MCP 2026-07-28 statelessness change is
drawing developer pushback as well as adoption: dropping the session
handshake in favor of routing on required headers reads to some
practitioners as the protocol converging back toward a plain API, sharpening
what MCP's durable value actually is (shared tool description and discovery,
not the session state it just removed).

Prior update: Azure API Management shipped a dedicated AI Gateway tier governing models,
MCP servers, and tools from one control plane in front of Foundry, Bedrock,
Vertex AI, and OpenAI — tool governance moving to the same managed-gateway
layer this page already tracks for auth.

Prior update: AWS published a secure MCP bridge that lets a cloud-hosted agent reach MCP
servers on a user's own laptop over a tunneled WebSocket connection, with no
open ports or VPN required — closing the cloud-to-local direction of the
tool-access gap. The harness itself is also now a named obstacle, not just
the tools it calls: OpenForgeRL trains harness-native agents (Claude
Code/Codex-style multi-turn loops) end-to-end via a model-call recording
proxy plus per-rollout Kubernetes containers, because existing RL stacks
can't express stateful, multi-process harness inference. Separately, MCP's
protocol layer now reaches past data and API access into deterministic
computation — Euclid-MCP delegates multi-step logical reasoning to a Prolog
backend through a standard MCP tool interface. A third addition targets the
call itself before it runs: an open-source static verifier plugs
formal-verification research into the harness to check a proposed tool call
against safety properties pre-execution, rather than only sandboxing or
scoping what happens after.

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
