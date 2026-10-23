---
title: "AWS Deep Insight splits multi-agent production work into five layers, each with its own control"
date: 2026-10-23
theme: production-evidence
evidence: [f4cbbc5a6a498cf5]
---
AWS's Solutions Architecture team (vendor-reported, open-sourced) frames production multi-agent systems as five problems: execution flow, per-agent model choice, reliable operation, safe execution of generated code, and monitoring.

Its answers: a Strands graph with a Supervisor calling Coder, Validator, Reporter and Tracker agents as tools; each agent in its own context passing only compressed results onward; Haiku for routing, Opus for planning, Sonnet for execution; a human approval step on the analysis plan; and per-session ephemeral Fargate sandboxes for code execution, with per-user isolation on AgentCore.

For builders: this is a worked checklist, not a benchmark. The post reports no quality, cost or latency numbers.
