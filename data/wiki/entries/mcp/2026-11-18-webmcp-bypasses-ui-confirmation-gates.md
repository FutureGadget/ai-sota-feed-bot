---
title: "WebMCP tools that skip the page's confirmation gates create accidental dark patterns"
date: 2026-11-18
theme: webmcp
evidence: [57d6500dc66aec75]
also: [agent-reliability]
---
With WebMCP, the in-browser agent shares the user's tab, cookies and state, but it reaches a transaction through a tool callback, not through the UI. The worked example is a ride quote that surges from €25 to €85. The page locks the button and asks the human to accept the new fare, while the agent calls the booking tool directly and books the €85 ride without approval.

Nobody intended the bypass. The frontend owned the gate, and the backend assumed every request had passed it. For builders: enforce prices, consent and other business prerequisites inside the tool handler or the server, never only in the rendered page. Treat each exposed WebMCP tool as a second entry point that needs the same checks as the screen.
