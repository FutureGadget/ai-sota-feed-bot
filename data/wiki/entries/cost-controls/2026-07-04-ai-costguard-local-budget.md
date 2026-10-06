---
title: "ai-costguard enforces a hard cost budget inside a single agent process"
date: 2026-07-04
theme: hard-caps
evidence: [769505c4770ec3dc]
also: [proving-agent-roi]
---
ai-costguard is a local TypeScript guardrail that **enforces hard cost budgets directly in the agent's runtime loop**, so a runaway agent trips a limit instead of consuming resources until someone notices.

It is the minimal form of the pattern: one process, one budget, checked in-process. Later tools extend the same idea across sessions and multi-agent runs.
