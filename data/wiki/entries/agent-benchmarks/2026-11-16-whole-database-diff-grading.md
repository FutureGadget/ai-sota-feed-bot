---
title: "Diffing the whole database after a computer-use task exposes collateral damage and false completion"
date: 2026-11-16
theme: trusting-the-score
evidence: [2867f3480e90e23f]
---
A small open benchmark runs computer-use agents against self-hosted business apps (Invoice Ninja, Dolibarr, Odoo 17 and 18). Every episode starts from the same snapshot, and afterwards the **entire database is diffed**.

That yields four verdicts instead of one pass/fail: success, **collateral damage**, **irreversible changes**, and **false completion** (the agent claims success the data contradicts). Phase 0 covers 635 scored episodes with Wilson intervals; the leading agent cost 1-3 cents per successful task (author-reported, one person's small sample).

For builders: grade state, not transcripts. A snapshot-and-diff harness over your own staging database catches the side effects a task-success check misses.
