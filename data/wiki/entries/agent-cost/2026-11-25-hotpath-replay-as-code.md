---
title: "Hotpath replays a recurring agent job as checked code, cutting a 1,000-run/day bill from $537 to $18"
date: 2026-11-25
theme: harness-and-context
evidence: [b5bbb28b9ab5357e]
also: [agent-planning]
---
Hotpath (Apache-2.0, local) records an agent's first run of a recurring job and replays it after that as checked code, falling back to the agent when something unusual happens. On the authors' synthetic benchmark, a job run 1,000 times a day costs about **$537/month** with a Sonnet agent versus **$18** replayed, or **$71** if one run in ten falls back. These are self-reported, small-sample numbers; the project says it does not help jobs that differ every run.

For builders: a daily report re-planned from scratch pays frontier prices for an unchanged decision. Freeze the plan into code, and keep the model for the exceptions.
