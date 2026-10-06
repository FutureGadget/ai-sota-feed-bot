---
title: "Cloudflare WriteGuard controls which write actions an agent may take through an MCP server"
date: 2026-08-19
theme: auth-and-governance
evidence: [e3560887ce822a61]
---
Cloudflare's **WriteGuard** (private beta) adds fine-grained security controls to MCP servers, governing agent access to tools that **modify data or perform actions** rather than only read.

Identity-provider auth answers who connects; this answers what the connection may then do, enforced on the server side.
