---
title: "E3 estimates task scope before executing and cuts cost 85% at equal success"
date: 2026-07-15
theme: ask-or-proceed
evidence: [8cdcaad96641fb63]
---
Agents often follow a maximum-context-first strategy, turning a one-line edit into a codebase audit. **E3 (Estimate, Execute, Expand)** estimates a minimal operating point, executes a minimum-sufficient path, and expands scope only when verification fails.

On a 121-edit benchmark it matches the strongest baseline's **100% success** while cutting cost **85%**, tokens **91%**, and files inspected **92%**. A live gpt-4o harness showed milder but real over-reading. Deciding how much work a task needs before executing is the cheapest fix for over-scoped plans.
