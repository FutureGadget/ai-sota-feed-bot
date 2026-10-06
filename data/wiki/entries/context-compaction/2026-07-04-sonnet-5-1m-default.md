---
title: "Claude Code makes a native 1M-token context window the default"
date: 2026-07-04
theme: skipping-compaction
evidence: [246a4c93052ef3c1]
also: [agent-memory]
---
Claude Code v2.1.197 made **Claude Sonnet 5** its default model, with a native 1M-token context window and promotional pricing of $2/$10 per Mtok through August 31.

Some long-horizon tasks can now skip compaction and retrieval by fitting more raw history in-window. That shrinks the set of tasks that need memory engineering; it does not remove it, since the window still resets between sessions.
