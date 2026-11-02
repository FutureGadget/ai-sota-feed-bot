---
title: "A logged-mistake corpus becomes executable Claude Code guards, each with a blocking test"
date: 2026-11-02
theme: deterministic-boundaries
evidence: [9aa08f9f02c4b235]
---
One developer ran Claude Code daily from June to October 2026 on real projects, including a shared git repo touched by several sessions. They had the agent log each repeated mistake. The log passed 500 records. They then turned seven into guards: hooks and pre-ship checks, each with a test showing it blocks the failure. A set of 50 mistakes is published alongside.

This is a single-author Show HN, not a measured result. The pattern is still reusable: convert recurring incidents into deterministic gates that run outside the model, rather than adding another prompt reminder.
