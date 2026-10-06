---
title: "Cloudflare adds agent spans to Workers traces, with truncation and uneven payload defaults"
date: 2026-08-16
theme: capture
evidence: [f07f7955a1ecbd39]
---
Cloudflare's agent tracing adds `invoke_agent` → `chat`/`execute_tool` → `tool_approval` spans to existing Workers traces, keyed by agent name, agent ID, and conversation ID. Sessions replay turn by turn.

The caveats are the news:
- Payload recording **defaults differ between its two supported SDKs** (off in one, on in the other).
- The docs warn traces are not lossless; payloads may be truncated.
- From October 1, 2026, **every span counts as a billable event**.

Check defaults per integration: one stack can over-retain personal data while another drops the tool arguments a debugging session needs.
