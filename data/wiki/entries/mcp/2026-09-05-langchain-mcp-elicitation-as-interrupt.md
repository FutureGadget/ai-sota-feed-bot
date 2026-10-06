---
title: "LangChain's MCP client maps elicitation to a LangGraph interrupt and caches tool lists"
date: 2026-09-05
theme: stateless-spec
evidence: [5b9d60084bc37024]
also: [tool-use]
---
LangChain's MCP support now lives in `langchain.mcp`, built on FastMCP for the 2026-07-28 spec. **Elicitation**, where a server pauses mid-call to ask the agent for more information, is handled as a LangGraph interrupt. Tool lists are cached instead of re-fetched per call.

A mid-tool-call question reuses the pause/resume primitive LangGraph already uses for human-in-the-loop, not a bespoke callback.
