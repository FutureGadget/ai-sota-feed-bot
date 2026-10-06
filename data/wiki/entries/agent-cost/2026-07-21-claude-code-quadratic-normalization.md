---
title: "Claude Code fixes harness bookkeeping whose cost grew quadratically with turns"
date: 2026-07-21
theme: harness-and-context
evidence: [44423c0a85b4d691]
---
Claude Code v2.1.216 fixed a slowdown where long-session **message normalization cost grew quadratically** with the number of turns, causing multi-second stalls and slow resumes. The same release split filesystem isolation from network egress control into separate sandbox settings, so a team can pay for each control only when it needs it.

The harness's own bookkeeping, not only its model calls, can make a long-running session slow and expensive. Profile the harness, not just the token bill.
