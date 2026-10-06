---
slug: mcp-stateless-scaling
title: "Why did MCP go stateless, and what does that change for scaling agent tool gateways?"
question: "Why did MCP go stateless, and what does that change for scaling agent tool gateways?"
summary: "MCP's 2026-07-28 spec dropped the session-handshake header that pinned a client to one server instance, so any gateway node can now handle any request: the statelessness trade that let HTTP scale horizontally, applied to agent tool calls."
status: active
cluster: tool-use
updated: 2026-10-06
audience: "strong-software-engineer"
related_topics: [mcp, tool-use]
related_playbook_cards: []
related_storylines: []
evidence:
  - id: aws-agentcore-mcp-2026-07-28-spec
    kind: story
    sid: b734d716b0d66f96
    title: "How AgentCore Gateway supports the MCP 2026-07-28 spec"
    added: 2026-08-08
    note: "AWS describes the spec's three changes: the `Mcp-Session-Id` handshake removed, with protocol version and client capabilities carried in each request's `_meta` parameter; governed extensions (SEP-2133) with reverse-DNS ids and independent release cadence; six SEPs aligning authorization with OAuth 2.0/OIDC. Gateway credential mechanisms (IAM/SigV4, OAuth/JWT) are unaffected. AgentCore operators enable the new version with one `UpdateGateway` call, no redeploy. Vendor write-up."
  - id: story-4daf9a3fc6b23a4c-azure-api-management-ai-gateway
    kind: story
    sid: 4daf9a3fc6b23a4c
    title: "Azure API Management Adds Dedicated AI Gateway Tier, Governing Models and MCP Tools"
    added: 2026-08-19
    note: "Within days of the spec change, Azure API Management shipped a dedicated AI Gateway tier fronting multiple model providers and MCP servers behind one MCP-aware control plane. Signals that vendors are building on stateless MCP routing; no performance data."
  - id: mcp-statelessness-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    added: 2026-08-08
    note: "The scaling implication mirrors HTTP: a stateful protocol needs sticky routing or a shared session store, both of which complicate load balancing and turn a lost instance into a dropped session. A stateless protocol lets any instance serve any request. That is plausibly why AWS could ship spec support as a configuration change rather than a re-architecture."
---

## Builder consequence
The MCP version you target decides whether a plain load balancer can front your MCP gateway fleet or whether you need sticky routing and a shared session store. The **2026-07-28 spec removed the protocol-level need for affinity**. If your gateway or client library still assumes a session handshake, you carry scaling complexity the spec no longer requires.

## Short answer
Earlier MCP opened with a handshake: the server issued an `Mcp-Session-Id` header, the client echoed it on every call, and each call had to land on the issuing instance. The 2026-07-28 spec removed that. Protocol version and client capabilities now travel in each request's `_meta` parameter, so any node can serve any call. The same revision added governed extensions (SEP-2133) and moved authorization toward standard OAuth 2.0/OpenID Connect.

## Builder model
This is the stateful-session versus stateless-HTTP choice.

- **Stateful:** follow-up calls must reach the instance holding session state. You pin clients (sticky sessions) or replicate state to a shared store, and a failed instance drops its sessions.
- **Stateless:** each request carries what the handler needs. The load balancer routes on capacity, and any healthy instance takes the next call.

MCP moved from the first to the second, so gateway fleets can behave like ordinary horizontally scaled web services.

## Mechanism
Before the change, the session identifier was the binding. Negotiated capabilities and protocol version lived only on the instance that issued the ID, so only that instance could interpret later calls correctly.

Now each request restates its protocol version and capabilities in `_meta`. Serving a call no longer depends on which instance served the previous one. "Stateless" applies to the protocol only: a tool implementation can still hold state such as a database connection or cache. The protocol just stops requiring request-to-request server affinity.

Two other changes shipped in the same revision and are independent of statelessness:

- **Governed extensions (SEP-2133).** Each capability gets a reverse-DNS id, its own repository and maintainers, and its own release cadence. Client and server negotiate support through an `extensions` capability map instead of a core version bump.
- **Authorization hardening.** Six SEPs align the spec with OAuth 2.0 and OpenID Connect patterns. They do not change how a given gateway validates inbound credentials.

## How to apply
- **Remove session-affinity infrastructure once clients and servers both speak 2026-07-28 or later.** Keep sticky rules only if something other than MCP needs them.
- **Verify library versions first.** Confirm your client and server libraries negotiate through `_meta`, not a lingering `Mcp-Session-Id` header, before dropping affinity routing.
- **Read the negotiated `extensions` map.** A matching core version does not mean a peer supports a given extension.
- **Audit gateway auth separately.** Upgrading the protocol version is not an inbound-auth upgrade.

## Failure modes
- Removing sticky routing while a library still uses the old handshake, silently breaking multi-call sessions.
- Confusing a stateless protocol with stateless tools; tool-level state remains an application decision.
- Treating the authorization SEPs as a credential upgrade for your gateway.
- Assuming extension support from a matching core version.

## Related
See [MCP](/topic/mcp) for the protocol's adoption arc and [tool use](/topic/tool-use) for tool-calling failures this scaling change does not address.
