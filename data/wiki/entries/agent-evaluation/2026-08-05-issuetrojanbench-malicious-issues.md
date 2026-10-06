---
title: "IssueTrojanBench tests whether coding agents execute instructions hidden in issues"
date: 2026-08-05
theme: coding-benchmarks
evidence: [adf13fffe0254841]
---
**IssueTrojanBench** benchmarks whether a coding agent executes a **malicious instruction smuggled inside an otherwise ordinary issue request**.

Issue text is untrusted input for any agent that picks up tickets automatically. This puts a number on that exposure; see [prompt injection](/topic/prompt-injection) for defenses.
