---
title: "MCP clients fail 64.4% of adversarial-context trials, and some attacks bypass the model"
date: 2026-10-06
theme: injection-paths
evidence: [b0a6adb95dddda44]
also: [mcp]
---
**COPEX** fixes the agent stack and varies only the tool-selecting model, so model susceptibility is not confused with guardrails or orchestration. It covers 25 attack types in 125 scenarios across four entry surfaces: model/agent, client, server/tool, and transport.

Across nine models and 3,375 trials, mean attack success was **64.4%** (58.3% to 71.4% by surface). Some client- and transport-level attacks succeed partly outside the model's view, so a better model alone cannot close them. Combined input and context scanning cut mean success by 49.6% on an eight-attack subset.

For builders: defend the MCP client and transport layers, not just the model.
