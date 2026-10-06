---
title: "Claude Code adds CLI login and logout for MCP servers"
date: 2026-06-23
theme: auth-and-governance
evidence: [f672838de330e86f]
---
Claude Code v2.1.186 adds **`claude mcp login` and `claude mcp logout`** to authenticate MCP servers without the interactive `/mcp` menu, with a `--no-browser` stdin flow for completing auth over SSH.

Server auth becomes scriptable and works on remote hosts, keeping the credential flow outside the agent's conversation.
