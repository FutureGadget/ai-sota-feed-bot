---
title: "Agentic fitness functions use an agent and versioned rubric to check architectural intent"
date: 2026-08-23
theme: grading-trajectories
evidence: [9472fcd4cb7a8f4b]
---
**Agentic fitness functions** pair an AI agent with a versioned rubric to evaluate judgment-heavy architecture properties — boundary fidelity, semantic contract drift, stale ADR assumptions — that deterministic rules cannot check.

Hard metrics can pass while design intent erodes. This extends rubric grading from output correctness to architectural conformance, run as continuous feedback in the build.
