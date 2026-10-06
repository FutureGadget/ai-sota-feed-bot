---
title: "Langy reads production traces, writes tests for failures, and opens a fix PR"
date: 2026-07-22
theme: eval-in-production
evidence: [d4af12d30d7453c4]
---
**Langy**, an AI engineer inside LangWatch, reads production traces, writes Scenario tests and evaluations for the problems it finds, opens a pull request on the repo, and proves the fix by running those simulations in CI. A human still merges.

The loop runs from "a trace shows a failure" to "a runnable eval and a proposed fix exist" without anyone writing either by hand.
