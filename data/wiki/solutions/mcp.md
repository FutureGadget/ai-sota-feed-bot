---
slug: mcp
kind: solution
title: "Model Context Protocol: a standard interface for agent tools"
status: active
obstacles: [tool-use]
related_storylines: []
evidence: [b2c537fce6444ae6, 8bad13df6e63105d, 6d71486170022687, 3c7fd2cd97de321f, 4f7d4f99793e131d, ff1510e381d9b329, 10de279350c1ecc9, f672838de330e86f, 9370d60ff069b1f4, cf37950940d3d2b5, 802363aee5105ca5, ca2de3ecb9f0eb55]
updated: 2026-06-30
covers_evidence: [b2c537fce6444ae6, 8bad13df6e63105d, 6d71486170022687, 3c7fd2cd97de321f, 4f7d4f99793e131d, ff1510e381d9b329, 10de279350c1ecc9, f672838de330e86f, 9370d60ff069b1f4, cf37950940d3d2b5, 802363aee5105ca5, ca2de3ecb9f0eb55]
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

Two further signs of maturation:

- **Tool discovery is becoming a scaling problem** — as a single agent faces dozens of connectors, listing every tool schema blows the context budget, so clients are shifting to *search* over the registry; OpenAI's Codex now uses MCP tool search by default, treating "find the right tool" as a retrieval step rather than dumping the full catalog.
- **What MCP carries is widening beyond tools**: reference data and memory now ride the same protocol — Mozilla's MDN MCP service (and community spinoffs that repackage browser-compat data as a queryable SQLite-backed server) expose knowledge, while Elastic's Atlas serves *agent memory* over MCP — so MCP is becoming the generic plug for tools, data, and state alike.

## What's new
Two maturation signals this round:

- **Tool discovery is now a retrieval step**: Codex makes MCP tool search the default so an agent searches the connector registry instead of loading every schema into context — the answer to connector counts outgrowing the context budget.
- **MCP is carrying more than tools**: Mozilla's MDN MCP service (plus community SQLite-backed spinoffs) serve reference data, and Elastic's Atlas serves agent *memory* over MCP, so the protocol is generalizing into the plug for tools, data, and state.

This rides on the prior shift to authentication as MCP's center of gravity
(`claude mcp login`/`logout`; the framing that MCP's real edge is isolating
the auth flow outside the agent's context window) and the now-assumed
infrastructure — MCP-equipped serverless runtimes (Azure Functions), a
filling small-server long tail, framework-free WebMCP clients (Persona.js,
MIT), and identity-provider-governed authorization.

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
