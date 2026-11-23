---
title: "Of 128 public reports on 50 agent harnesses, 15% describe full recovery from a failure"
date: 2026-11-23
theme: execution-and-identity
evidence: [295f69cfd2192ad5]
also: [agent-orchestration]
---
*Exercised, Rarely Recovered* graded eight recovery mechanisms across 12 persistent runtimes, 26 coding harnesses, and 12 research runtimes with a frozen protocol and two blind coding passes. Of 128 real-use reports, **19** describe full recovery, 54 partial, and 45 failed. Checkpoint/resume fully recovered in 1 of 27 reports and rollback in 1 of 15. No harness compensates external side effects, and research runtimes' guarantees appear only on benchmarks.

For builders: a checkpoint restores the agent's state, not the world it touched. Design idempotent tools and explicit compensation for anything the agent writes outside its sandbox.
