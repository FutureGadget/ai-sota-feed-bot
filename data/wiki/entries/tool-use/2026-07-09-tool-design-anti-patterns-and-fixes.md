---
title: "Bloated schemas and vague names are the main MCP tool-design failures; lazy loading halves context"
date: 2026-07-09
theme: discovery-and-definitions
evidence: [2e309060a5831bee]
also: [mcp]
---
AWS's MCP tool-design guide names two failure modes:

- **Bloated context**: every tool schema loads on every call, used or not.
- **Confusion**: vague parameter names and oversized result payloads make the model pick the wrong tool or call the right one wrong.

Its fix progression runs from the raw API exposed as-is, through richer descriptions and `Literal`-typed constraints, to lazy-loaded taxonomies behind a discovery tool. The leanest design cut per-turn context use **from 4% to 2%**. The guide cites Anthropic's lazy-loading work at up to 85% token reduction and suggests capping a tool at roughly eight parameters.
