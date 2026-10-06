---
title: "Chronicle replays agent runs from a cut point to make regression tests reproducible"
date: 2026-09-18
theme: eval-in-production
evidence: [fd9660f034d371fa]
---
Agent failures depend on non-bitwise-reproducible inference, tools that read changing state, and multi-step trajectories, so re-running a failing case from scratch often does not reproduce it. **Chronicle** adds **cut-point replay**: resume a recorded trajectory from a chosen point to test whether a code or prompt change fixes the failure.

Existing tooling records runs to trace or score them; this records them to test changes. Replaying part of a trajectory is the practical unit for reproducible agent regression tests.
