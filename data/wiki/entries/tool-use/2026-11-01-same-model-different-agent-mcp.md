---
title: "Same model scored 17 points apart on MCP servers depending on the agent harness"
date: 2026-11-01
theme: calling-reliability
evidence: [b78023b26122d472]
---
The M3 MCP-testing project ran Claude Haiku 5.5 against 21 real MCP servers (about 20 tasks each, three trials per task) through two coding agents. Via OpenCode it answered **82.0%** correctly from the server; via Claude Code, **65.4%**. The authors attribute the gap to built-in tools each agent reaches for first, not the model (vendor-reported, self-run).

For builders: an MCP server's measured accuracy is a property of the model *and* harness pair. Test your server through every agent your users run, and don't carry a model-only score across harnesses.
