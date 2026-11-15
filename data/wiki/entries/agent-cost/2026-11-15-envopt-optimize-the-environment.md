---
title: "Reorganizing the agent's environment, not its model or harness, cut agent cost 48%"
date: 2026-11-15
theme: harness-and-context
evidence: [13244a5e59c39757]
---
**EnvOpt** treats the environment as a third tuning knob. A research agent runs the target agent on shared workspaces, data stores, or repos, reads the trajectories, and rewrites how the data is held and exposed: new databases, restructured files, new endpoints. It may not touch the harness.

Across five benchmarks, EnvOpt cut cost on held-out tasks by **48% on average** at equal or higher pass rates. Most savings came from smaller tool results; output tokens fell about 20%. One optimization run cost about **$150** on AutomationBench. Optimized environments transferred to other harnesses and stronger models (vendor-reported).

For builders: if many tasks hit the same Slack, ticket store, or repo, how it is exposed is a cost lever. Plain files beside an MCP server is one such choice.
