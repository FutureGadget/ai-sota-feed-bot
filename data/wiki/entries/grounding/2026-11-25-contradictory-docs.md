---
title: "Contradictory docs: coding agents spot the conflict yet follow the wrong page, costing up to 38% more tokens"
date: 2026-11-25
theme: adversarial-evidence
evidence: [9ff473bf95fb89a0]
also: [agent-reliability]
---
Microsoft tested three contradictions that had been live in Dev Proxy's documentation, with three models and about **140** agent runs. Agents often noticed the two pages disagreed and still followed the wrong one first. When the mistake broke something visible, such as a 404, every agent recovered, but the detour added up to **38%** more tokens. Mistakes that stayed silent until CI were the costly case.

For builders: doc drift is a grounding failure for agents, not just a reader annoyance. Reconcile reference pages, how-tos, and samples together, and give agents a visible check that fails fast.
