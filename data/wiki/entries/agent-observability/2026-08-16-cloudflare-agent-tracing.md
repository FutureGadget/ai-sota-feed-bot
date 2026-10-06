---
title: "Cloudflare adds native agent tracing, with truncated payloads and opposite privacy defaults"
date: 2026-08-16
theme: trace-capture
evidence: [f07f7955a1ecbd39]
---
Cloudflare added agent spans to existing Workers traces: `invoke_agent`, `chat`/`execute_tool`, and `tool_approval`, keyed by agent name, agent ID, and conversation ID, so a session replays turn by turn.

The gotchas are concrete:

- **Payload recording defaults differ by framework**: off under Vercel's AI SDK, on under Flue. Those payloads often carry personal data or secrets.
- Traces are not lossless; payloads may be **truncated**, dropping the arguments a debug session needs.
- From October 1, 2026, every span is a billable event.
