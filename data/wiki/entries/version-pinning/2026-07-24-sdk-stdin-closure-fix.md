---
title: "SDK 0.2.127 fixes background tasks silently bypassing PreToolUse hooks"
date: 2026-07-24
theme: transitive-pinning
evidence: [90726831e1877773]
---
Before `claude-agent-sdk` 0.2.127, `query()` closed stdin on the first result frame even while background tasks were running. Their SDK-MCP tool calls failed with "Stream closed" and **silently bypassed PreToolUse hooks**. The release fixes that and bumps the bundled CLI to 2.1.219.

A pin held one version too early keeps a real defect, here one that skips your own guard hooks. "Patch" does not mean "safe to skip".
