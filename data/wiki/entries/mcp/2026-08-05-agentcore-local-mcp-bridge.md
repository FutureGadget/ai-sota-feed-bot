---
title: "AWS bridges cloud-hosted agents to MCP servers on a user's laptop with no open ports"
date: 2026-08-05
theme: servers-in-production
evidence: [ea850b1a9c912609]
also: [tool-use]
---
AWS built a secure **MCP bridge** so a Bedrock AgentCore agent running in the cloud can call MCP servers on a user's own laptop. Signed messages tunnel over the existing WebSocket connection through a browser extension and Chrome native messaging, **with no inbound ports or VPN**.

It reverses the usual direction (a cloud agent reaching local tools and files) using the same protocol, not a bespoke remote-access tool.
