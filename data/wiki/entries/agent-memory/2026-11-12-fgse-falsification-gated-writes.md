---
title: "Testing a lesson as a hypothesis before committing it held harmful memory updates to 3.6%"
date: 2026-11-12
theme: recall-and-curation
evidence: [99e35db5c56c4bd6]
---
Falsification-Gated Self-Evolution (FGSE) treats each experience-derived lesson as a structured hypothesis with a precondition, a behavior change, an expected effect, and a verifier. The lesson is applied only in a temporary state and tested on three probe sets: target transfer, falsification, and archived regressions. It is then committed, refined, or rejected on measured gain and risk.

The paper reports 39.8 WebArena success, 78.8 AppWorld average completion, and 0.724/0.487 Pass^1 on tau-Retail/tau-Airline, with regression damage at 1.3% and harmful committed updates at 3.6%. Paper-reported; it needs an environment with a verifier.

For builders: gate memory writes the way you gate code. Stage the update, run a regression set of archived tasks, and commit only on a measured gain.
