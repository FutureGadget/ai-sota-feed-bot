---
title: "DoorDash's shopping assistant keeps the LLM to orchestration and language"
date: 2026-07-13
theme: production-runtimes
evidence: [d4d5677e2459e3ab]
---
Ask DoorDash splits work across specialized agents, **MCP-based tooling**, and a separate intelligence layer with persistent consumer memory and live backend data, rather than one model deciding everything. DoorDash reports up to 24% higher checkout conversion and 17% larger baskets from memory-backed sessions (company-reported).

The pattern narrows what the model owns: deterministic and specialized components carry the task, and the LLM routes and talks.
