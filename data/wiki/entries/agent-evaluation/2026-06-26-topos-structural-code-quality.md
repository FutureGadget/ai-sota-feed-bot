---
title: "Topos scores agent-written code on structural quality, not just passing tests"
date: 2026-06-26
theme: coding-benchmarks
evidence: [7ef376842f782ecd]
---
**Topos** maps a codebase to program graphs (AST, CFG, CPG, MDG) and computes structural metrics on agent-written code. The premise: "tests passing" no longer justifies a merge, and the human cost of reviewing agent contributions is the new bottleneck.

For code agents the eval question becomes "is this change good", not only "does it run".
