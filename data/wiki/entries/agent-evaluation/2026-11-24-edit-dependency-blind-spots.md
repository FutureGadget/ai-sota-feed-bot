---
title: "Coding agents leave broken callers after an edit, and SWE-bench-style tests often fail to catch it"
date: 2026-11-24
theme: coding-benchmarks
evidence: [ab5bcea7ed94a195]
also: [agent-benchmarks]
---
*Edit-Induced Dependency Mismatch* audited real coding-agent trajectories on DeepSWE, SWE-bench Verified, and FeatureBench. After editing a function, agents kept reasoning from stale dependency judgments still sitting in context and left defects in consumer code. The original task tests often did not detect them, so the run scored as a pass. Recovery earlier in a trajectory could coexist with these omissions at the end.

For builders: a green task test does not prove callers still work. Add checks that exercise every consumer of an edited symbol, and re-show the agent the current caller code after it changes an interface.
