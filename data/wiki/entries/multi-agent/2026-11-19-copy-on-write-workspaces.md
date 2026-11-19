---
title: "APFS copy-on-write gives each parallel coding agent a fully installed checkout in about 100ms on macOS"
date: 2026-11-19
theme: parallel-coding-agents
evidence: [fce40b3a174eefcb]
---
Replica builds a project tree once (checkout, `node_modules`, build output) and clones it with APFS `clonefile` for every agent run, so each agent gets its own real git checkout in about **100ms** instead of seconds to minutes of install. Automatic cleanup keeps total disk use bounded.

The bottleneck it targets is small-file creation and deletion, where macOS is slowest. For builders running several coding agents on one laptop: isolate them with filesystem clones rather than shared worktrees plus reinstalls; startup time and disk, not tokens, cap how many run in parallel. Timings are author-reported.
