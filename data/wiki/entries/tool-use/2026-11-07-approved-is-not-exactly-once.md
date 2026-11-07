---
title: "Human approval is not exactly-once: crash-and-resume replays an approved payment"
date: 2026-11-07
theme: production-runtimes
evidence: [385b20a2401d6d5d]
also: [agent-orchestration]
---
Call4Agents, a dependency-free Python library from a single author (Show HN, self-reported), targets a gap in approval flows: a "yes" from a human does not make a tool call run once. Its write-up replays one approved payment followed by a crash and a documented resume, and reports **2 payments** in LangGraph, Pydantic AI and the OpenAI Agents SDK.

The library wraps the agent you already run, including an MCP server, so approved calls execute at most once after a retry.

For builders: treat approval and idempotency as separate controls. Give every side-effecting tool call a stable key recorded before execution, and test resume-after-crash on your own harness.
