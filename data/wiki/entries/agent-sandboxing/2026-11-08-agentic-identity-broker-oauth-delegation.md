---
title: "Zalando's Agentic Identity Broker gives agents scoped, revocable OAuth access to MCP services"
date: 2026-11-08
theme: credential-boundary
evidence: [d2e1d4bcf8eebaac]
also: [mcp]
---
The Agentic Identity Broker (AIB) is an MIT-licensed OAuth2 broker from the Zalando Incubator. A user delegates access to an AI agent, and the agent receives a scoped, revocable grant to MCP services instead of the user's own credentials.

This matches the credential-boundary pattern: authority is issued per agent and can be withdrawn without rotating the user's secrets. The source is a Show HN post by a co-author, so there are no independent production results yet.

For builders: if agents call MCP servers with a shared or personal token, a broker like this is a reference design for delegating instead.
