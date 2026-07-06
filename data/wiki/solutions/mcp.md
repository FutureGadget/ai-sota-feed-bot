---
slug: mcp
kind: solution
title: "Model Context Protocol: a standard interface for agent tools"
status: active
obstacles: [tool-use]
related_storylines: []
evidence: [b2c537fce6444ae6, 8bad13df6e63105d, 6d71486170022687, 3c7fd2cd97de321f, 4f7d4f99793e131d, ff1510e381d9b329, 10de279350c1ecc9, f672838de330e86f, 9370d60ff069b1f4, cf37950940d3d2b5, 802363aee5105ca5, ca2de3ecb9f0eb55, 2b0cc93ba8a0f9b8, 3c227e4c9b2cd2eb]
updated: 2026-07-06
covers_evidence: [b2c537fce6444ae6, 8bad13df6e63105d, 6d71486170022687, 3c7fd2cd97de321f, 4f7d4f99793e131d, ff1510e381d9b329, 10de279350c1ecc9, f672838de330e86f, 9370d60ff069b1f4, cf37950940d3d2b5, 802363aee5105ca5, ca2de3ecb9f0eb55, 2b0cc93ba8a0f9b8, 3c227e4c9b2cd2eb]
---

## TL;DR
The Model Context Protocol (MCP) is a standard way to describe, discover, and
call tools so any MCP-speaking agent can use any MCP server. It collapses the
N×M problem of bespoke integrations into a common interface — the agent
equivalent of "speak HTTP" instead of writing a custom client per service.

## State of the art
MCP is moving from a client-side convenience to **production infrastructure**.
Vendors are shipping official servers — HashiCorp's Terraform MCP server reached
GA so agents can drive Terraform Registry APIs, and reference builds wire up SaaS
servers (Amazon Quick, Cisco Webex) into working assistants.

The actuation surface is expanding to the **browser**: WebMCP is in Chrome
origin trials, letting a site expose JavaScript functions and HTML forms as
tools to an in-page agent. The open-source client side is filling in
alongside the browser trial, with MIT, framework-free libraries (Persona.js)
that ship native WebMCP so any site can build agentic experiences without a
vendor SDK.

MCP is also becoming the assumed plug for **hosted runtimes** — Azure
Functions' agents runtime gives every agent MCP server access (alongside
1,400+ connectors) out of the box — and the long tail keeps filling in with
small task servers (e.g. a "coding tools" MCP that hands any agent file/shell
coding primitives).

Crucially, the protocol's growth is forcing the **governance** layer —
Claude's enterprise managed authorization provisions MCP connectors org-wide
through an identity provider (Okta first), so connector access and
authorization are configured centrally rather than per user. That move from
"connect a tool" to "govern a fleet of connectors" is the sign of a maturing
standard.

The same maturation is landing in the client tooling: Claude Code added
`claude mcp login` / `logout` to authenticate servers from the CLI without
the interactive menu, and practitioners increasingly argue MCP's *core*
value is exactly this — isolating the **auth flow** outside the agent's
context window (and ideally out of the harness entirely) rather than the
tool-description format itself. Read that way, the durable win of MCP is
credential handling, not schema standardization.

That governance push is now backed at the **protocol** level: the MCP
project promoted its Enterprise-Managed Authorization extension to stable
status, replacing per-server consent prompts with a single sign-on flow
through an org's identity provider. It generalizes what Claude's enterprise
auth already did for one vendor into a spec any MCP client or server can
implement.

Two further signs of maturation:

- **Tool discovery is becoming a scaling problem** — as a single agent faces dozens of connectors, listing every tool schema blows the context budget, so clients are shifting to *search* over the registry; OpenAI's Codex now uses MCP tool search by default, treating "find the right tool" as a retrieval step rather than dumping the full catalog.
- **What MCP carries is widening beyond tools**: reference data and memory now ride the same protocol — Mozilla's MDN MCP service (and community spinoffs that repackage browser-compat data as a queryable SQLite-backed server) expose knowledge, while Elastic's Atlas serves *agent memory* over MCP — so MCP is becoming the generic plug for tools, data, and state alike.

That "more than tools" widening now includes **work distribution**: TaskPeace
is a task queue that coding agents pull work *from* over MCP, using the
protocol as the plug for a job queue rather than a single tool call or a
data/memory fetch — a third payload type alongside tools and knowledge/state.

## What's new
The auth push that started as a vendor feature is now a **stable protocol
extension**: MCP's Enterprise-Managed Authorization reached stable status,
giving any client or server a spec for zero-touch, identity-provider-backed
access instead of per-server consent prompts.

That builds on the same trajectory as MCP's other recent widening — work
distribution (TaskPeace's task queue over MCP), tool discovery as a
retrieval step (Codex's default MCP tool search), and reference data/memory
riding the protocol (MDN MCP service, Elastic Atlas) — alongside the
now-assumed infrastructure of MCP-equipped serverless runtimes (Azure
Functions), a filling small-server long tail, and framework-free WebMCP
clients (Persona.js, MIT).

## Trade-offs
A shared protocol buys interoperability and reuse, but every connector you expose
is a new permission and a new attack surface — MCP standardizes *access*, which
makes authorization and blast-radius the hard part (see
[prompt injection](/topic/prompt-injection)). It also adds a moving dependency:
server quality, versioning, and uptime become yours to manage, and a misbehaving
or malicious server is now reachable by every agent that speaks the protocol.
Best when you have many tools and many agents; overkill for a single hardcoded
integration.

## Why it matters for platform engineers
MCP is the integration layer you adopt instead of writing API wrappers — it
turns tool connectivity into a fleet you provision and govern (identity-provider
auth, per-connector permissions) rather than scattered glue code. The platform
job shifts accordingly: from building connectors to running a connector
registry safely, which is squarely an infra-and-security responsibility.
