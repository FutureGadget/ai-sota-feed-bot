---
title: "Codex compaction now counts retained images against the token budget"
date: 2026-08-28
theme: harness-and-context
evidence: [0577669e18ed3998]
---
Codex 0.150.1 makes remote compaction **count retained images toward its token budget by default**, trimming the oldest images as needed.

Before, accumulated screenshots could inflate the context re-sent every turn without showing up in the compaction budget. Agents that work from screenshots should account for images as tokens, not as free attachments.
