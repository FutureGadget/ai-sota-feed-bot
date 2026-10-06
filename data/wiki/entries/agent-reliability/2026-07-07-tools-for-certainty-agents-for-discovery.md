---
title: "NVIDIA splits agent platforms into deterministic tools for certainty and agents for discovery"
date: 2026-07-07
theme: deterministic-boundaries
evidence: [ed7d246a0b0ba7d9]
---
In an InfoQ talk, NVIDIA's Aaron Erickson describes purpose-built agent hierarchies that separate **tools for certainty** (deterministic code you can trust) from **space for the model's own discovery**. He pairs the split with LLM-as-judge test pyramids and warns against the paradox of choice: giving an agent too many options lowers reliability.

Deciding which parts of a task get deterministic treatment becomes an explicit architecture decision, made at design time, rather than something left to the model at run time.
