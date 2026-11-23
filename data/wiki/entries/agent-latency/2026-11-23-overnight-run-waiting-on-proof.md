---
title: "An overnight Claude Code run spent 66% of wall clock on UI tests and simulator checks, 26% on the model"
date: 2026-11-23
theme: beyond-the-engine
evidence: [26a3da6a312086c4]
also: [agent-reliability]
---
A developer timed a 14.6-hour run in which a manager session drove 11 feature agents plus Opus and Codex reviewers. UI test runs took **33%** of wall clock and simulator checks and video another **33%**; model thinking and writing took **26%**, code review 5%, builds 1%. Single-class UI test runs happened 191 times, and fix rounds after review took a third of the night.

The planned fixes are structural, not model-side: two features in parallel, each with its own worktree and simulator, reviews started on commit, the full UI suite once per feature, and nit findings deferred to one polish pass. For builders: profile the verification loop before buying a faster model.
