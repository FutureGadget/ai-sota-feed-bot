---
title: "DoorDash automates stale feature-flag cleanup with multi-agent LLMs: 45 of 50 usable PRs"
date: 2026-09-18
theme: production-evidence
evidence: [2547415be8ec24a2]
---
DoorDash built a multi-agent system to retire stale feature flags across **more than 60,000 flags and 623 repositories**. It combines live experimentation data over MCP, an engineer-approval step, isolated git worktrees, parallel agents, and automated validation.

In an evaluation of 50 flags, **45 produced usable pull requests, averaging 13.8 minutes and $4.79 per cleanup**. Internal platform upkeep fits well: bounded tasks, a verifiable result, and a human approving each change.
