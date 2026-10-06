---
title: "Agentic overlays wrap existing REST services as MCP tools without rebuilding them"
date: 2026-06-28
theme: agent-native-surfaces
evidence: [d6f47c6e7ea5d37c]
---
AWS and co-authors describe **agentic overlays**: thin wrapper layers in front of existing REST services that expose them as MCP-compatible tools and let them take part in Agent-to-Agent (A2A) interactions, without changing the underlying system.

This is the brownfield answer to "rebuild agent-native". It trades the cleanliness of purpose-built endpoints for reuse of what already runs in production.
