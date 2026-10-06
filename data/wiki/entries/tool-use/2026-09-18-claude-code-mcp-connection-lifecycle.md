---
title: "Claude Code makes MCP startup hangs and mid-session disconnects visible and boundable"
date: 2026-09-18
theme: calling-reliability
evidence: [6726c9df5fadbf36, 5744b97e5a176886]
also: [mcp]
---
Two Claude Code releases harden the MCP client's connection lifecycle:

- v2.1.273 notifies the user when an MCP server **disconnects mid-session** and automatic reconnection gives up, pointing at `/mcp`.
- v2.1.274 adds `CLAUDE_CODE_MCP_STARTUP_WAIT_MS` to **bound how long the first non-interactive turn waits** for MCP servers to connect (`0` = don't wait).

Both were silent failures before: a hung startup and a dropped session nobody notices. Headless runs can now set an explicit startup budget.
