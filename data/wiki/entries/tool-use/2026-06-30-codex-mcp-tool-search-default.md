---
title: "Codex switches MCP tools to tool search by default"
date: 2026-06-30
theme: discovery-and-definitions
evidence: [cf37950940d3d2b5]
also: [mcp]
---
Codex 0.142.2 makes **MCP tools use tool search by default** where the model and provider support it, keeping compatibility with older ones.

Once an agent reaches dozens of connectors, listing every schema in the prompt burns context and degrades which tool the model picks. Tool discovery becomes a retrieval step instead of a context dump.
