---
title: "SWE-Touch tests coding agents when a user edits the code mid-task"
date: 2026-08-05
theme: domain-suites
evidence: [c101d5e1e7e169c1]
---
**SWE-Touch** stress-tests coding agents in a shared workspace with validated **Counter-Edits**: plausible user edits to task-relevant code that conflict with completing the task, made while the agent is still working.

Repository benchmarks usually assume an uninterrupted solo run. Real pairing with a coding agent doesn't work that way.
