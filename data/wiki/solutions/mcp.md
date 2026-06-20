---
slug: mcp
kind: solution
title: "Model Context Protocol: a standard interface for agent tools"
status: active
obstacles: [tool-use]
related_storylines: []
evidence: [b2c537fce6444ae6, 8bad13df6e63105d, 6d71486170022687, 3c7fd2cd97de321f, 4f7d4f99793e131d, ff1510e381d9b329]
updated: 2026-06-20
covers_evidence: [b2c537fce6444ae6, 8bad13df6e63105d, 6d71486170022687, 3c7fd2cd97de321f, 4f7d4f99793e131d, ff1510e381d9b329]
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
servers (Amazon Quick, Cisco Webex) into working assistants. The actuation
surface is expanding to the browser: WebMCP is in Chrome origin trials, letting a
site expose JavaScript functions and HTML forms as tools to an in-page agent.
MCP is also becoming the assumed plug for hosted runtimes — Azure Functions'
agents runtime gives every agent MCP server access (alongside 1,400+ connectors)
out of the box — and the long tail keeps filling in with small task servers
(e.g. a "coding tools" MCP that hands any agent file/shell coding primitives).
Crucially, the protocol's growth is forcing the **governance** layer — Claude's
enterprise managed authorization provisions MCP connectors org-wide through an
identity provider (Okta first), so connector access and authorization are
configured centrally rather than per user. That move from "connect a tool" to
"govern a fleet of connectors" is the sign of a maturing standard.

## What's new
MCP is now assumed infrastructure: hosted serverless runtimes ship with MCP
access built in (Azure Functions' agents runtime), the small-server long tail is
filling out (a generic coding-tools MCP), and authorization is moving to
identity-provider governance — the boring, load-bearing pieces, not just demos.

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
