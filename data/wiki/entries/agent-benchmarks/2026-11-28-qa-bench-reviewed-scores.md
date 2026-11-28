---
title: "A vendor's QA Bench run beats the reference agent on score but loses on precision"
date: 2026-11-28
theme: trusting-the-score
evidence: [a8c73489adab6130]
---
Pluswithai published every run and verdict of its QA agent on Momentic's open QA Bench: 20 areas across four apps (Gitea, Metabase, Saleor, Twenty), three 30-minute runs each. A script recomputes every number. Score is the severity sum minus incorrect and duplicate reports.

The vendor-reported totals put it ahead of Momentic's agent on confirmed bugs (**236 vs 177**) and narrowly on score (**398 vs 385**). Precision is lower, at **72% vs 85.5%**. The totals include the vendor's own review of findings the official grader left unmatched, and that review raised many area scores. Repository code went from 27.3 to 44.3.

For builders: a findings benchmark rewards volume. Compare precision and the grader's pre-review numbers, not the headline score.
