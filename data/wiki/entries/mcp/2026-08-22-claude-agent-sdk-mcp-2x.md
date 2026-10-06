---
title: "Claude Agent SDK for Python supports MCP 2.x alongside 1.x for in-process servers"
date: 2026-08-22
theme: stateless-spec
evidence: [a6959f9ba4dbb368]
also: [tool-use]
---
claude-agent-sdk-python v0.2.140 widens its dependency to `mcp>=1.23.0`, supporting **mcp 2.x alongside 1.x**. In-process SDK MCP servers now use mcp's own in-memory transport instead of hand-rolled JSON-RPC dispatch, so hand-built `mcp.server.Server` instances pass resources, prompts, and all result content types through verbatim.

The harness's dependency version and the protocol version its in-process servers speak are less tightly coupled.
