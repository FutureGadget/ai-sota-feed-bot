---
title: "Budget large JSON tool results by whole items and tell the model exactly what was cut"
date: 2026-11-25
theme: curating-the-working-set
evidence: [6151c01b70c401a5]
also: [tool-use]
---
`agent-tool-result-reducer` is a zero-dependency Python function that sits between a tool returning data and that data entering context. It fits a response into a character budget by selecting fields, dropping the widest fields first, and truncating only on **whole-item boundaries**. Every result carries a `_meta` block stating what the model did and did not receive.

For builders: blind string truncation of tool output gives the model half a record and no signal that data is missing. Trim structurally and disclose the cut, so the agent can ask for the rest instead of reasoning from a partial list.
