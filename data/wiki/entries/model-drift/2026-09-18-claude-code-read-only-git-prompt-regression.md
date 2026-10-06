---
title: "Claude Code fixes a regression that made read-only git commands prompt again"
date: 2026-09-18
theme: regressions-and-reverts
evidence: [2a68cabb6c20de64]
---
claude-code v2.1.270 fixed **read-only git commands in Bash asking for permission** after a session had been running a while, a regression introduced in v2.1.269.

Permission behavior regressed and recovered across two adjacent patch releases. In unattended runs, an unexpected prompt is a stall, not an inconvenience.
