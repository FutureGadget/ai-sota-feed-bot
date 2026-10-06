---
title: "DoorDash cleans stale feature flags with MCP-fed agents at $4.79 per cleanup"
date: 2026-09-18
theme: production-runtimes
evidence: [2547415be8ec24a2]
also: [mcp]
---
DoorDash built a multi-agent system to clean up stale flags across **more than 60,000 flags and 623 repositories**. It pulls live experimentation data through MCP, gates each cleanup on engineer approval, and runs parallel agents in isolated Git worktrees with automated validation.

In an evaluation of 50 flags, 45 produced usable pull requests at an average of **13.8 minutes and $4.79 per cleanup** (company-reported). MCP here is the access layer into internal engineering systems, not a customer-facing feature.
