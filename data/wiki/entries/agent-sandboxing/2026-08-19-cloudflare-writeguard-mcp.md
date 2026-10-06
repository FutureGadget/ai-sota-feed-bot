---
title: "Cloudflare WriteGuard adds fine-grained controls on MCP tools that modify data"
date: 2026-08-19
theme: permission-policy
evidence: [e3560887ce822a61]
---
Cloudflare's **WriteGuard**, in private beta, adds fine-grained security controls for MCP servers. It targets tools that **modify data or perform actions**, rather than those that only read.

Splitting read from write at the MCP layer lets a team expose read tools broadly and gate the small set of state-changing calls where injection does damage.
