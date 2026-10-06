---
title: "Chronicle replays recorded agent runs from a cut point to regression-test code changes"
date: 2026-09-18
theme: drift-tooling
evidence: [fd9660f034d371fa]
---
Agent failures are hard to reproduce: inference is not bitwise deterministic, tools read changed state, and re-runs rarely repeat a long trajectory. **Chronicle** records a run at its non-deterministic boundaries as immutable envelopes, and its **cut-point replay** resumes from a chosen point in the saved trajectory to test a code change against it.

Reproducing a drift-caused failure is a separate problem from detecting one. Replay isolates the regression without re-triggering the volatile conditions.
