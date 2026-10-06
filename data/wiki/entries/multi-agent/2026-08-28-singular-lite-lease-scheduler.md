---
title: "singular-lite assigns coding tasks via lease records and a reaper, not agent self-reports"
date: 2026-08-28
theme: parallel-coding-agents
evidence: [4b510cf3587ed730]
---
singular-lite is a three-tier scheduler for parallel coding agents: one origin reconciler, per-area planners, and isolated-worktree workers. It hands out **JSON lease records** instead of trusting an agent to report back, and a separate **reaper process attributes completions and failures** by checking the dispatch record.

Crash-safe assignment comes from state the orchestrator owns, not from the agent's own status update. Early-stage project with no production adoption signal.
