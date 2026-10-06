---
title: "Claude Code cost estimates now include the 1.1x data-residency premium"
date: 2026-08-25
theme: vendor-spend-controls
evidence: [31d0f6b1d6dddfa7]
also: [agent-cost]
---
Claude Code v2.1.239 folds the **1.1x US-only-inference premium** that data-residency workspaces pay into `/cost`, the status line, and `--max-budget-usd`.

Before the fix, a team on a residency-locked workspace budgeted against the base rate and paid 10% more. A budget cap is only as good as the estimate it compares against, so the estimate needs the same scrutiny as the cap.
