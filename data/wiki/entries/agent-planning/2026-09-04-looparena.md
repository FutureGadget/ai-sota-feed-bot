---
title: "LoopArena scores the loop's guidance separately from the coding agent's capability"
date: 2026-09-04
theme: measuring-planning
evidence: [c989986c344e129f]
---
In loop engineering, a controller monitors progress, assigns work, runs checks, and decides what the agent does next. **LoopArena** benchmarks models in that controller role: whether the loop trusts a **stale progress note**, **skips verification**, or **stops before the task is safe to submit**.

A single end-to-end pass/fail cannot tell whether the agent or the loop caused the outcome. LoopArena separates them.
