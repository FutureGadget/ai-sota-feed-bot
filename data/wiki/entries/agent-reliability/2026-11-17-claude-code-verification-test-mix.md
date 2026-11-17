---
title: "Claude Code team bets on end-to-end, property, and differential tests to let agents verify their own work"
date: 2026-11-17
theme: verifying-the-work
evidence: [9a0aa0e71b450c03]
---
With about **90%** of its code written and reviewed by Claude, the Claude Code team treats verification loops as what allows dozens of parallel agents instead of one or two. A separate rubric grader improved structured-file task success by up to **10 points** over a plain prompting loop (vendor-reported).

The team favors three test types. **End-to-end** tests are hardest to fool: a skill boots and drives the real app. **Property** tests probe round-trip, invariant and idempotency edge cases agents miss. **Differential** tests compare optimized code against a naive reference.

Flaky tests teach the agent to rerun instead of fix, and slow tests get run less. A repeated failure becomes a hook or a CLAUDE.md rule.
