---
slug: mcp
kind: solution
title: "Model Context Protocol: a standard interface for agent tools"
status: active
obstacles: [tool-use]
related_storylines: []
evidence: []
updated: 2026-10-06
themes:
  - key: stateless-spec
    title: The stateless spec and what MCP is actually for
    summary: The 2026-07-28 spec made MCP stateless and clients are catching up, which sharpens the debate over whether its value is discovery and auth isolation or just another API.
  - key: auth-and-governance
    title: Authorization and governance of connector fleets
    summary: Connector access is now provisioned through identity providers and managed settings, with gateways and server-side write controls deciding what a connection may do.
  - key: webmcp
    title: WebMCP and the browser as a tool surface
    summary: WebMCP lets web pages expose functions and forms as tools; it moved from a Chrome origin trial to a one-click Cloudflare toggle and agent browsers that call it.
  - key: servers-in-production
    title: Vendor servers and hosted deployments
    summary: Infrastructure and SaaS vendors now ship official MCP servers and managed gateways, but GA does not yet mean every major client can connect.
  - key: beyond-tools
    title: Beyond tool calls - knowledge, memory, work, and computation
    summary: MCP now carries reference data, agent memory, task queues, symbolic reasoning, and execution primitives, making it a general plug for anything an agent consumes.
---

## TL;DR
The Model Context Protocol (MCP) is a standard way to describe, discover, and
call tools so any MCP-speaking agent can use any MCP server. It collapses the
N×M problem of bespoke integrations into one interface: the agent equivalent
of "speak HTTP" instead of writing a custom client per service.

## State of the art
**MCP is production infrastructure now.** Infrastructure and SaaS vendors ship
official servers, clouds host the tool loop and front MCP servers with managed
gateways, and the browser is becoming a tool surface through WebMCP. The
payload has widened past tool calls to reference data, agent memory, task
queues, and deterministic computation.

**The protocol itself just changed shape.** The 2026-07-28 spec made MCP
stateless, added governed extensions, and hardened authorization. Remote
servers can drop sticky sessions and scale like any stateless service, and
clients and SDKs are adopting the new version.

**Governance is where the work moved.** Connector access is provisioned
through identity providers rather than per-user consent, managed settings
decide which servers exist at all, and gateways and server-side controls
decide what a connection may write. Production security guidance treats this
as layered defense, not one gateway setting.

**The open question is what MCP is for.** Statelessness makes it look like
"just an API" to some developers. The durable value is the shared
tool-description and discovery layer and keeping credentials out of the
agent's context, which matters most where an agent cannot call APIs freely.
Interop is also unfinished: a server can reach GA while major clients still
cannot connect because of identity-provider gaps.

Tool-definition quality and catalog search, the main levers for making many
MCP tools usable at once, are tracked on [tool use](/topic/tool-use).

## Trade-offs
A shared protocol buys interoperability and reuse, but every connector you
expose is a new permission and a new attack surface. MCP standardizes
*access*, which makes authorization and blast radius the hard part (see
[prompt injection](/topic/prompt-injection)).

It also adds a moving dependency: server quality, spec versions, and uptime
become yours to manage, and a misbehaving or malicious server is reachable by
every agent that speaks the protocol. The stateless spec simplifies scaling but
pushes state, retries, and idempotency back onto your own layers.

Best when you have many tools and many agents. It is overkill for a single
hardcoded integration, or for a fully trusted terminal agent that can call
APIs directly.

## Why it matters for platform engineers
MCP is the integration layer you adopt instead of writing API wrappers. It
turns tool connectivity into a fleet you provision and govern
(identity-provider auth, managed server lists, per-connector write controls)
rather than scattered glue code.

The platform job shifts from building connectors to running a connector
registry safely: tracking spec versions across clients and servers, checking
which clients your identity provider can actually admit, and treating each
server as a dependency with its own security review.
