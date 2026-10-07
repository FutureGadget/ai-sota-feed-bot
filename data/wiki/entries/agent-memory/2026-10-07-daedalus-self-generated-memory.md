---
title: "DAEDALUS bootstraps agent memory from self-generated tasks, with no oracle verifier"
date: 2026-10-07
theme: recall-and-curation
evidence: [63c206dfd946c7ff]
---
An explorer agent invents challenging-but-solvable tasks in a new environment and a solver attempts them. Each solver failure yields a heuristic, which is **accepted into the memory bank only after the solver repeatedly succeeds with it in context**.

On AppWorld, τ²-bench, and AutomationBench the authors report up to +15.9 points mean success and up to 2.2x pass^5 over a no-memory baseline, competitive with methods that need training tasks. Heuristics also transferred to other model families.

For builders: gating writes on repeated success is a cheap write-time curation rule that needs no human-written guidelines.
