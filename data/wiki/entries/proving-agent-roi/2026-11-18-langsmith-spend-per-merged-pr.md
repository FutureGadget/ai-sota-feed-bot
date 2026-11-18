---
title: "LangSmith attributes coding-agent spend to pull requests, including spend that never produced one"
date: 2026-11-18
theme: per-task-attribution
evidence: [2a783f6259dc0b2d]
also: [cost-controls]
---
LangSmith added **outcomes** for coding agents. GitHub pull requests and GitLab merge requests are linked back to the traced threads that produced them, across Claude Code, Codex and other providers. Attribution handles one thread opening several PRs and one PR taking several threads. A dashboard shows what a merged PR cost and how much spend never led to a PR, with before/after trends when a team switches models.

For builders, this moves the ROI unit from tokens per user to cost per merged change. A merged PR is still a proxy, not proof of value: it ignores review load and reverts.
