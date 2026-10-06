---
title: "LangSmith Trajectories shows an agent session as one readable thread, not a span tree"
date: 2026-09-24
theme: reading-traces
evidence: [b60131f089d99489]
---
LangSmith's **Trajectories** renders a whole agent session as a conversational thread: user turns, tool calls, and subagent handoffs read top to bottom, instead of the nested span tree a generic OpenTelemetry viewer shows.

It trades completeness of the tree for the job that bottlenecks debugging long-running agents: scanning a session fast enough to spot where it went wrong.
