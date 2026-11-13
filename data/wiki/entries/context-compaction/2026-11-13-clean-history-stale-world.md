---
title: "A history edited to look clean lowers recovery when the world still holds the error"
date: 2026-11-13
theme: compaction-safety
evidence: [567d8273d9c1fb0d]
also: [agent-reliability]
---
Researchers froze agents mid-task, edited either the history or the world state, and let a receiver model continue. The same correct content helped or hurt depending on how the history stated it.

- **Truthful note beside the preserved error:** recovery rose from 51% to 66% on AgentCE-Bench.
- **Error rewritten as the agent's own completed action:** recovery fell from 50% to 44%, below the unedited history.
- **Success receipt for a database write whose effect is absent:** AppWorld task success fell from 45% to 28%. Once the effect was present, the same receipt raised it from 38% to 49%.

For compaction, repair, and handoff: annotate mistakes instead of erasing them, and never summarize a write as done without checking the world. Paper-reported.
