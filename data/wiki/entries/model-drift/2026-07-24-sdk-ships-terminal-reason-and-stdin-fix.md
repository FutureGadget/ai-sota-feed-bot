---
title: "SDK adds terminal_reason and typed usage, then fixes a bug that skipped PreToolUse hooks"
date: 2026-07-24
theme: bundled-cli-bumps
evidence: [a19f1341e900df0e, 90726831e1877773]
---
Two releases broke the cosmetic pattern:

- **v0.2.126** adds `ResultMessage.terminal_reason` (why the loop ended: `completed`, `max_turns`, `aborted_streaming`, ...) and types `model_usage` per model. Both are load-bearing for retry and cost logic.
- **v0.2.127** stops `query()` closing stdin on the first result frame while background tasks run. Before, SDK-MCP tool calls from background subagents failed with "Stream closed" and **silently bypassed PreToolUse hooks**. It also bumps the CLI to v2.1.219.

Real API surface and a hook-bypass fix ship in the same stream as cosmetic bumps.
