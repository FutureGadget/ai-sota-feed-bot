---
title: "Claude Code permission rules can now match a tool's input parameters"
date: 2026-06-21
theme: harness-controls
evidence: [9ef99508d91d13ed]
---
Claude Code v2.1.178 adds `Tool(param:value)` syntax for permission rules, matching a tool's input parameters with `*` wildcards; for example, `Agent(model:opus)` blocks Opus subagents.

Permissions move from allow-or-deny per tool to allow-or-deny per argument. That is the granularity least privilege needs, because the same tool can be safe with one input and dangerous with another.
