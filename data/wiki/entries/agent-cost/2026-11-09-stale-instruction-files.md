---
title: "Stale AGENTS.md instructions add hidden tool calls that task-success metrics miss"
date: 2026-11-09
theme: harness-and-context
evidence: [569b9613f4d348fe]
---
A study of 732 coding-agent trajectories (two models, 22 maintenance tasks, three real stale instructions: a test command, a code location, a procedure) finds agents follow stale guidance when it is relevant, even when correct information exists elsewhere. On the stale test command, Claude Sonnet 5.5 needed about two extra tool calls per run, a third more than with the corrected command; the other two cases showed no detectable difference. Agents recovered from the failures but none repaired the instruction file. Correcting the file removed operations on obsolete paths; deleting the instruction prevented most. Paper-reported.

For builders: instruction files are read every session, so staleness is a recurring cost. Audit them against the code, and prefer fewer instructions.
