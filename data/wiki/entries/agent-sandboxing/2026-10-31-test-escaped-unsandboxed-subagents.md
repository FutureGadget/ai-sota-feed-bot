---
title: "A parallel subagent's test escaped an unsandboxed Mac and spoke aloud on the host"
date: 2026-10-31
theme: local-sandboxes
evidence: [86590a88b2c59c59]
also: [agent-observability]
---
An incident report (single user, 2026-10-28, Claude Code 2.1.286 in auto mode) describes seven background subagents closing GitHub issues in parallel git worktrees on a macOS host with no sandbox. One agent's test ran against the real machine, and the Mac began reading JSON aloud in two overlapping synthetic voices. The author traced it through agent transcripts and the macOS unified log.

Worktrees isolate files, not the host: tests, speech, and other side effects still reach the real OS. Run parallel agents in a container or VM, and keep transcripts to reconstruct what ran.
