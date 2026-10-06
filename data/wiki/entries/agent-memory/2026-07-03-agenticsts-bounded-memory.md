---
title: "AgenticSTS frames long-horizon memory as a contract about what each decision may see"
date: 2026-07-03
theme: measuring-memory
evidence: [a026d7598baf3bcf]
---
**AgenticSTS** is a testbed for long-horizon agent memory. Its bounded contract builds every decision from a fresh message assembled by **typed retrieval**, with no raw cross-decision transcript appended, so the prompt stays bounded across runs of any length.

Appending everything makes past context easy to reach but leaves the effect of any single memory component impossible to isolate. A bounded contract makes memory components measurable one at a time.
