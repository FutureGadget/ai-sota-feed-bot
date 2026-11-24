---
title: "Snap's MCP gateway requires each agent call made for a person to pass as both the person and the agent"
date: 2026-11-24
theme: auth-and-governance
evidence: [5ffb2e252de57ff5]
also: [prompt-injection]
---
Snap's central MCP Gateway fronts **60+ MCP servers and 1,100+ tools**; people and its internal agent made about **1.6 million** tool calls through it in one week, with several million more from service accounts. Early tests showed identity breaking mid-chain: a downstream service saw the MCP server's service account, and an agent-opened PR appeared to come from a GitHub app instead of the engineer. The rule Snap settled on: when an agent acts for a person, the call must be authorized for **both** identities.

For builders: a gateway that forwards only the agent's credential either over-grants or breaks. Propagate the human principal end to end and authorize against the intersection of both.
