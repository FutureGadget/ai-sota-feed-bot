---
title: "Lovable exposes each published app as an MCP capability alongside its human UI"
date: 2026-08-28
theme: agent-native-surfaces
evidence: [738f130d6895192c]
also: [mcp]
---
Lovable is branching into MCP-powered **"capabilities"**, which CTO Fabian Hedin defines as a part of an application an agent can call directly without a human opening the app. A published app gets two interfaces: the human UI and an MCP endpoint any MCP client can call.

A connector gateway keeps credentials server-side and encrypted; generated app code gets a short-lived key scoped to one user instead of a secret. The protocol argument now reaches the individual SaaS app, not only infrastructure vendors.
