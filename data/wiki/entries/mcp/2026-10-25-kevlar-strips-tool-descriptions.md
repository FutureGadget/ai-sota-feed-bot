---
title: "Kevlar blocks MCP tool-description injection by stripping every description field"
date: 2026-10-25
theme: auth-and-governance
evidence: [a92a400264dfa863]
also: [prompt-injection]
---
Kevlar is an open-source MCP firewall posted to Show HN, a single self-described project. A malicious MCP server can use tool descriptions to redirect the model, pull credentials, or add tools. Kevlar sets every `description` to `""` on each `tools/list` response before the client sees it, so the LLM gets only the name and `inputSchema`.

It also rebuilds `inputSchema` from an allowlist, dropping prose fields such as `title`, `examples`, and `$comment`, and validating enum values, keys, `$ref` targets, and types against the MCP spec.

For builders: this trades away description-driven tool selection for a smaller injection surface. Names and schemas must then carry the meaning.
