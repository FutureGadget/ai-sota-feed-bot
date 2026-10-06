---
title: "Securing MCP in production needs four control layers, not just a gateway"
date: 2026-07-29
theme: auth-and-governance
evidence: [9352c956aa90126f]
also: [tool-use]
---
An InfoQ article by Nik Kale lays out **defense in depth for MCP** across four architectural layers: safe execution, management infrastructure, outbound trust, and semantic integrity. It argues enforcement has to sit at the earliest trustworthy control point, not only at the gateway.

Securing MCP is a layered architecture decision, not one gateway setting. See [prompt injection](/topic/prompt-injection) and [agent sandboxing](/topic/agent-sandboxing) for what it defends against.
