---
title: "Passing tests is not mergeable: agents violate 43.1% of repository policies"
date: 2026-10-06
theme: coding-benchmarks
evidence: [4508ce1f38669dd3]
---
**SWE-CC** turns the contribution docs of 12 open-source repositories into **823 machine-checkable atomic policies** (style, git, testing workflow), each backed by a deterministic checker. It audits both the agent's runtime steps and its final patch across 500 tasks extended from SWE-bench Verified.

Across four LLMs and two scaffolds, agents that produce functionally correct patches still violate **43.1%** of applicable policies, and nearly half of the violations happen in intermediate execution steps rather than in the diff.

For builders: unit-test pass rate overstates merge readiness. Encode your own repo's contribution rules as deterministic checks and grade the trajectory, not only the patch.
