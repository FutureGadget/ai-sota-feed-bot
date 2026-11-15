---
title: "Risk-tiered human approval let Claude Code double merged PRs while cutting the revert rate over 40%"
date: 2026-11-15
theme: verifying-the-work
evidence: [c16da948123691c6]
---
The Claude Code team moved verification ahead of human review. Before a PR opens, the agent runs tests, builds, and linters, and a second agent reviews the diff in a fresh context. Then several agent reviewers investigate findings independently, another group verifies them, and a security review can block the merge.

Human approval scales with risk: **none** for docs or flagged-off features, **one** reviewer for medium risk, **two** for high risk, and always for CI workflows. Review loops stop after **three rounds**.

From June to September, merged PRs more than doubled and the share needing a revert fell by **over 40%**. First-round pass rose from **65% to 78%** (vendor-reported). For builders: spend human attention by risk tier, and cap agent review rounds.
