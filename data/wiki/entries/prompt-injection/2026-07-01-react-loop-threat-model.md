---
title: "Agent vulnerabilities split across context, reasoning, and tool execution in the ReAct loop"
date: 2026-07-01
theme: agent-authorization
evidence: [61a5c70b3cae54c5]
---
Sriram Madapusi Vasudevan's InfoQ talk locates agent vulnerabilities separately in **context** (what gets read in), **reasoning** (what the model decides), and **tool execution** (what it may do). It names memory poisoning and rogue tool execution as the concrete failure modes.

The recommended response is defense in depth: layered controls plus an LLM-as-judge critic reviewing the agent's decisions, structured against a named threat model (MAESTRO) rather than ad hoc rules.
