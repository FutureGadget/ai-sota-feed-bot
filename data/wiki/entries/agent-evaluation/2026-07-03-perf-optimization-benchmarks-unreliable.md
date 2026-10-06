---
title: "Performance-optimization benchmarks conflate runtime noise with agent progress"
date: 2026-07-03
theme: score-validity
evidence: [20cd66043e9dab55]
---
A study of repository-level performance-optimization benchmarks (**GSO, SWE-Perf, SWE-fficiency**), which score coding agents by comparing patched runtime against baselines and reference patches, finds their leaderboard scores can conflate runtime instability and benchmark-specific scoring choices with real capability.

The problem is not only that benchmarks are unrepresentative; their own numbers can be noisy.
