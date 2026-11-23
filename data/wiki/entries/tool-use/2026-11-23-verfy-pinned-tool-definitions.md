---
title: "Verfy pins MCP tool definitions by hash and blocks a tool whose description changed after approval"
date: 2026-11-23
theme: guarding-the-call
evidence: [bdedb1e4ef84ac62]
also: [mcp]
---
Verfy, an MIT-licensed CLI, locks the SHA-256 of each approved MCP tool definition. When a server ships an update that rewrites a tool description, `verfy lock check` fails and its gateway hides the tool and denies the call. It also guards Claude Code tool calls by reading scripts before execution, flagging, for example, the line in an innocuous-looking `python fix.py` that would delete the home folder, and it issues signed receipts.

For builders: approving a tool once is not enough when the server can change it; pin definitions the way you pin dependencies.
