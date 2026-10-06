---
title: "Online evals can wait days to grade an agent against the real downstream outcome"
date: 2026-07-15
theme: eval-in-production
evidence: [8d0381b4e9af78ba]
---
Inngest's guide to online versus offline evals describes an **online eval** that defers judgment — pausing for up to several days — until the downstream event the task was supposed to cause actually happens.

The agent is graded on what it caused, not on what it claimed at finish time. Offline evals stay the fast pre-merge check; online evals catch what only production outcomes reveal.
