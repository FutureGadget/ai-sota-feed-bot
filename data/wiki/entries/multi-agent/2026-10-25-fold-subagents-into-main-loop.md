---
title: "Anthropic: fewer subagents plus progressive disclosure can cut cost and latency"
date: 2026-10-25
theme: when-it-pays
evidence: [13225fd2d3574734]
---
Anthropic's guidance for Claude Platform agents says to fold some subagents back into the main agent loop and rely on progressively disclosed context and tools instead. The vendor claims quality improves while cost and latency drop. Each subagent carries its own context window, so every split adds a handoff.

A migration kit runs a guided workflow: it identifies your subagent patterns, evaluates alternatives, and verifies the chosen approach. It ships with a demo on a mock system to try before touching a real agent. The post gives no benchmark numbers in the excerpt, so treat the gains as vendor-reported.

For builders: audit each subagent for whether it needs isolation. If it exists only to hold context, loading that context on demand in one loop is cheaper to run and debug.
