---
title: "Weir tests whether agents leak credentials by planting unique fake keys"
date: 2026-11-01
theme: credential-boundary
evidence: [da0666cb075514bf]
---
Weir targets a specific leak path: agent frameworks copy keys into traces and logs, and coding agents read them into model context. `weir-run` plants a unique fake key wherever a real one would live, runs the agent's own flows against a local fake model, and captures everything sent out. It finds each key by exact value, names where it went, and never prints it. A companion mode checks which real keys a Claude Code session exposed.

For builders: it is a single Show HN project with no independent results, but exact-value tracing is a cheap CI check for key hygiene.
