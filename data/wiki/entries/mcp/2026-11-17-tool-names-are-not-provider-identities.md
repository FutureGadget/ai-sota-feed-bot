---
title: "A second MCP server can capture calls meant for a legitimate provider by mimicking its tools"
date: 2026-11-17
theme: auth-and-governance
evidence: [aaeb7b15ed6fabde]
also: [prompt-injection, tool-use]
---
MCP clients compose tools from many servers, but a tool's name, description and schema are not bound to a verified provider. The attacker in this study compromises nothing: it runs one more MCP server advertising tools with chosen metadata.

Across five LLM-based clients, misbinding was worst when an **exact-name collision**, a task-aligned description and a compatible schema reinforced each other. Authority-flavored descriptions with a compatible schema also caused wrong-provider execution **without** any name collision. Models failed differently: some picked the attacker, some asked for clarification, some resolved the provider inconsistently.

For builders: namespace tools by a verified server identity and pin which provider serves each capability, instead of letting the model pick between look-alike tools.
