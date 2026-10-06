---
title: "Claude Code permission rules can match a tool's input parameters"
date: 2026-06-21
theme: permission-policy
evidence: [9ef99508d91d13ed]
---
Claude Code v2.1.178 added **`Tool(param:value)` syntax** (with `*` wildcards) for permission rules, for example `Agent(model:opus)` to block Opus subagents. The same release has auto mode's classifier evaluate subagent spawns.

Authorization becomes per action, not per tool: allow a tool generally but deny the specific argument values that carry risk or cost.
