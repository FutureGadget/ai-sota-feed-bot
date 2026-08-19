---
slug: mcp-stateless-scaling
title: "Why did MCP go stateless, and what does that change for scaling agent tool gateways?"
question: "Why did MCP go stateless, and what does that change for scaling agent tool gateways?"
summary: "MCP's 2026-07-28 spec dropped the session-handshake header that pinned a client to one server instance, so any gateway node can now handle any request — the same statelessness trade that let HTTP scale horizontally, applied to agent tool calls."
status: active
cluster: tool-use
updated: 2026-08-19
audience: "strong-software-engineer"
related_topics: [mcp, tool-use]
related_playbook_cards: []
related_storylines: []
evidence:
  - id: aws-agentcore-mcp-2026-07-28-spec
    kind: story
    sid: b734d716b0d66f96
    title: "How AgentCore Gateway supports the MCP 2026-07-28 spec"
    note: "Describes the spec's three changes: elimination of the session-handshake, an `Mcp-Session-Id` header that previously pinned clients to a server instance; requests now carry protocol version and client capabilities inside a self-contained `_meta` parameter instead; a governed extensions system (SEP-2133) giving each new capability a reverse-DNS identifier, its own repository, and independent release cadence instead of forcing core spec version bumps; and six SEPs hardening the authorization spec toward closer OAuth 2.0/OpenID Connect alignment, while existing gateway-level credential mechanisms (IAM/SigV4, OAuth/JWT) are unaffected."
  - id: story-4daf9a3fc6b23a4c-azure-api-management-ai-gateway
    kind: story
    sid: 4daf9a3fc6b23a4c
    title: "Azure API Management Adds Dedicated AI Gateway Tier, Governing Models and MCP Tools"
    note: "Azure API Management shipped a dedicated AI Gateway tier fronting multiple model providers and MCP servers behind one MCP-aware control plane within days of the 2026-07-28 spec change."
  - id: mcp-statelessness-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    note: "The scaling implication is the same one HTTP's statelessness solved decades ago: a stateful protocol requires session affinity (sticky routing to the instance holding the session) or a shared session store, both of which complicate load balancing and turn losing one instance into a dropped session; a stateless protocol lets any instance serve any request because the request carries what it needs, which is what let AWS ship spec support as a config change on an existing gateway rather than a re-architecture."
covers_evidence:
  - aws-agentcore-mcp-2026-07-28-spec
  - story-4daf9a3fc6b23a4c-azure-api-management-ai-gateway
  - mcp-statelessness-editorial-synthesis
---

## Builder consequence
If you run or plan to run an MCP gateway or a fleet of MCP servers behind one, the protocol version you target decides whether you can put a plain load balancer in front of them or need sticky routing and a shared session store. MCP's 2026-07-28 spec removed the protocol-level reason you'd need the latter. If your gateway or client library still assumes a session handshake, you're carrying scaling complexity the spec no longer requires.

## Short answer
Earlier MCP versions opened a connection with an initialization handshake: the server issued an `Mcp-Session-Id` header, and the client had to send it back on every following call, which meant that call had to land on the same server instance that issued it. The 2026-07-28 spec — the largest revision since MCP launched — removed that handshake. Each request is now self-contained: protocol version and client capabilities travel inside the request's own `_meta` parameter, so any gateway node can service any call. The same revision also formalized a governed extensions system (SEP-2133) so new capabilities ship independently of the core spec, and hardened the authorization spec toward standard OAuth 2.0/OpenID Connect patterns.

## Builder model
Treat this the same way you'd treat choosing between a stateful WebSocket session and stateless HTTP requests. A stateful protocol needs every follow-up call routed to the specific instance holding that session's state — you either pin the client to that instance (sticky sessions) or replicate the state to a shared store every backend can read. Either way, that instance failing mid-session drops the session's context with it. A stateless protocol removes that constraint by having each request carry what a handler needs to serve it, so a load balancer can route purely on capacity and any healthy instance can pick up the next call. MCP moving from the former to the latter is a protocol-level decision to make gateway fleets behave like ordinary horizontally scaled web infrastructure instead of like a session-affine service.

## Mechanism
Before the 2026-07-28 spec, an MCP client opened a session with an initialization exchange, and the server responded with a session identifier the client was required to echo on every subsequent request. That identifier was the mechanism binding a client to one server instance: whichever instance issued the session ID was the only one that could correctly service later calls in that session, because session state (negotiated capabilities, protocol version) lived on that instance and nowhere else by default.

The new spec drops the handshake and the header. Instead, the protocol version and the client's capabilities are included directly inside the `_meta` parameter of each request. Nothing about serving a given call depends on which instance served the previous one, because the previous call's context isn't implicitly required — the current call restates what it needs. That is what "stateless" means here concretely: not that MCP servers can't hold state at all (a tool implementation can still be stateful in whatever way it needs), but that the *protocol* no longer requires request-to-request server affinity to interpret a call correctly.

Two other changes shipped in the same revision, distinct from statelessness but bundled into the same spec bump: a governed extensions system (SEP-2133) that gives each new protocol capability a reverse-DNS identifier, a dedicated repository with delegated maintainers, and its own release cadence — so a client and server negotiate which extensions they both support via an `extensions` capability map, instead of every new feature forcing a core version bump; and six SEPs that bring MCP's authorization specification closer to standard OAuth 2.0 and OpenID Connect deployment patterns, without changing how a specific gateway's inbound credential check (IAM/SigV4, OAuth/JWT) is implemented.

## Evidence
- Story-backed: the AWS AgentCore Gateway writeup names the specific mechanism change (session-handshake header replaced by a self-contained `_meta` parameter) and the two accompanying spec changes (governed extensions via SEP-2133, six authorization-hardening SEPs), and reports that AgentCore Gateway operators enable the new spec version via a single `UpdateGateway` call rather than a redeployment.
- Story-backed: Azure API Management shipping a dedicated AI Gateway tier as a control plane spanning multiple model providers and MCP servers within days of the spec change, evidence that the ecosystem is building on the assumption that MCP traffic can be routed statelessly.
- Editorial inference: the load-balancing and failover framing (sticky routing vs. stateless routing, HTTP's own history of this trade-off) is LLM Digest's synthesis connecting the protocol change to standard distributed-systems scaling practice; it is not a claim from either source article.

## How to apply
- **Drop session-affinity infrastructure once your MCP clients and servers both speak the 2026-07-28+ spec.** Sticky load-balancer rules or a shared session-ID store are no longer required by the protocol; keep them only if something else in your stack (not MCP itself) still needs them.
- **Check your MCP client/server library version before assuming statelessness.** A library built against a pre-2026-07-28 spec version may still perform the old handshake; confirm the library negotiates via the `_meta` parameter, not a lingering `Mcp-Session-Id` header, before removing affinity routing.
- **Treat extension support as negotiated, not assumed.** With SEP-2133, a server can support an extension your client doesn't know about, or vice versa; check the negotiated `extensions` capability map rather than assuming a feature is available because the spec version matches.
- **Re-verify your gateway's inbound auth separately from the spec bump.** The authorization hardening changes the *specification's* alignment with OAuth 2.0/OIDC; it does not automatically change how your specific gateway validates inbound credentials, so upgrading the protocol version is not itself an auth upgrade.

## Failure modes
- Assuming statelessness before your stack supports it: removing sticky routing while a client or server library still relies on the old session-handshake header silently breaks multi-call sessions.
- Conflating "stateless protocol" with "stateless tools": the protocol no longer requires server affinity to route a call correctly, but a tool implementation behind the gateway can still hold state (a database connection, a cache) — that's an application-level design choice, not something the spec decides for you.
- Treating the authorization SEPs as a credential-mechanism upgrade: they align the spec with OAuth 2.0/OIDC conventions, but your gateway's actual inbound auth check doesn't change unless you change it.
- Skipping the extension negotiation check: assuming a peer supports an extension because both sides report the same core protocol version, when SEP-2133 extensions are negotiated independently of core version.

## Related
See [MCP](/topic/mcp) for the protocol's broader adoption arc and [tool use](/topic/tool-use) for the wider set of agent tool-calling failure modes this scaling change doesn't address.
