---
title: "TokenOps checks a shared run budget before every model call across agent processes"
date: 2026-09-08
theme: hard-caps
evidence: [5210d1c245b93480]
---
TokenOps wraps every model call and **checks a shared run budget before execution**. It sits in the execution path, not beside it like a tracing dashboard. Multiple agent processes read and write one SQLite ledger, so a budget can span a distributed multi-agent workflow.

Its ten policies go beyond a hard stop: throttle, log, mutate the prompt, or inject cost-reduction instructions. The project reports cutting wasted agent spend by up to 65%, but **publishes no methodology or independent benchmark** behind that figure.
