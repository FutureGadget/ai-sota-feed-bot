---
title: "Logslim compacts build and test output before the agent reads it"
date: 2026-06-22
theme: curating-the-working-set
evidence: [c763e01254fa7c5c]
---
Logslim strips noise from verbose test and build logs **before** they enter a coding agent's context, instead of summarizing them afterward.

This is compaction at the input boundary: a deterministic pre-compactor needs no model call and never runs a lossy summary over the agent's own reasoning. For coding agents that read build output every step, it is the cheapest place to cut the per-step token bill.
