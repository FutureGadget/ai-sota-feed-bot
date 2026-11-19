---
title: "Reversibility classes for 536 MCP tools gated every attributable attack run that a read/write split missed"
date: 2026-11-19
theme: guarding-the-call
evidence: [905f6a523982b910]
also: [agent-sandboxing]
---
Permission to call a tool says nothing about whether a mistake can be undone. This paper declares a **five-level reversibility vocabulary** with argument-sensitive rules, conservative defaults and a contract for capturing prior state, applied to **536 tools across 20 MCP servers**.

On 2,158 recorded runs, the session guard gated the action in **all 29** attributable attack runs, against 18 for a plain read/write proxy, while adding nine approval points across 1,209 benign runs. Native MCP annotations disagreed with the registry for 118 of 481 tools. Recovery experiments show undo depends on what state was captured. For builders: classify tools by undo cost, not read/write, and do not trust server-supplied annotations as that class.
