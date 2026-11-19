---
title: "Databricks says trace analysis kept it on Opus 4.8 and that fixing MCP errors saves about $1.2M a year"
date: 2026-11-19
theme: attribution
evidence: [80f6a46612979bf7]
also: [agent-tracing, proving-agent-roi]
---
Databricks reports three savings it found in its own agent traces rather than in budgets: offline replays showed **no gain from upgrading Opus 4.8 to Opus 5**, so it stayed on the cheaper model; fixing common **MCP errors** recovered an estimated **$1.2M a year**; and simple prompts were reaching expensive models, which led it to adopt routing. It is launching Unity Gateway Insights, which uses Genie to analyze agent traces for these patterns. All figures are vendor-reported.

For builders: replay traces before every model upgrade, and count failed tool calls as spend; retries are a cost line, not only a reliability one.
