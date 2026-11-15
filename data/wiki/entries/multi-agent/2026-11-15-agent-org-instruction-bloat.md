---
title: "A self-organizing coding-agent org grew its rulebook 10.5x until 23% of PRs were blocked only by paperwork"
date: 2026-11-15
theme: production-evidence
evidence: [05186f5f8665ca0b]
also: [context-compaction]
---
Perfloop runs its engineering as a fleet of coding agents on Amp. Left to organize themselves, the agents added an executive layer, review committees, 386 numbered compliance grants, and threads that watched other threads. Instruction files grew from **26,401 to 277,486 characters** in three months, with agents writing 208 of 249 October commits to them.

An audit found **23%** of PRs blocked only by redundant process, against **11%** caught by real CI or review gates. After a reset, the coordinator only routes work, and every gate must name a real failure it prevents. Weekly merges then reached **1,119 PRs** (vendor-reported).

For builders: agents only add rules and every new thread obeys them all. Cap and prune instruction files on a schedule.
