---
title: "Voice agents can run tools while the user is still speaking, cutting final-response latency 36%"
date: 2026-10-21
theme: less-work-per-step
evidence: [52090699e3b64ede]
---
Speculative voice agents that cut off generation at each transcript update can truncate a tool call before its arguments are complete. Heartbeat Thinking instead starts a new reasoning pass on the latest partial transcript at intervals, while earlier passes and already-dispatched tools run to completion. A shared record of finished reasoning and tool results fills in missing arguments and starts dependent calls.

Paper-reported, on FDBench v3 against a windowed speculative baseline:
- Tool coverage up 16 percentage points.
- Mean final-response latency down 36.4%.

Effects on final task quality vary by benchmark.
