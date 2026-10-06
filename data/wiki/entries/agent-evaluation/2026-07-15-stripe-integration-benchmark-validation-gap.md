---
title: "Stripe's integration benchmark shows agents build code but fail to validate it"
date: 2026-07-15
theme: coding-benchmarks
evidence: [aebd52611d2bd6be]
---
Stripe's **11-environment** agent-integration suite covers checkout migration, billing API work, and full-stack browser checkout. On full-stack tasks Claude Opus 4.5 scored **92%** against GPT-5.2's 73%, but both models' failures were in **validation**, not code generation: misreading an HTTP 400 as success, or losing track of a form after a tool interaction moved focus out of an input field.

An agent that writes working code but cannot tell whether it worked is what a pass/fail outcome score hides.
