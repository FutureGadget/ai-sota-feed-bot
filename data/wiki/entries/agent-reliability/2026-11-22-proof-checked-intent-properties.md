---
title: "Proof-checked properties catch agent code that misses intent, but cannot say whether the property was right"
date: 2026-11-22
theme: verifying-the-work
evidence: [cd7b95a68a3ad7e7]
---
Microsoft Research's neuro-formal verification (NFV) derives formal properties from a pull request's description and issues. An agent then tries to prove the code has each property, and Lean or Dafny checks the proof. On 38 recent PRs it checked **217 properties**. Every verdict is proved (with its assumptions), refuted (with a counterexample), or unresolved. Allowing "unresolved" raised accuracy: **92%** of NFV's verdicts were right, against 72% for a model asked directly, whose answers came with nothing to check.

The analysis warns that a proof covers only its property. It cannot show the property mattered, was proved about the code that runs, or says what you meant. For builders: freeze properties before the agent writes code, and still review them.
