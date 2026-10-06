---
title: "Boundary contracts took Haiku 4.5 from 13/19 rule violations to 0/20"
date: 2026-06-22
theme: cheaper-models
evidence: [c32171008fef614c]
---
ANMA's author found cheaper models ignore architecture rules. Unguided, Claude Haiku 4.5 **violated its constraints in 13 of 19 runs**; wrapped in explicit boundary contracts (YAML rules plus `CLAUDE.md`, hooks, and CI checks) it **violated them in 0 of 20**.

A bit of contract overhead can make a cheap model reliable enough to take the bulk of the work from a frontier one. This is a small, self-reported benchmark from the tool's author, so rerun it on your own codebase.
