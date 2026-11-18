---
title: "A two-week Claude chaos loop with 11-30 sub-agents hardened a launch to 60 errors in 2B requests"
date: 2026-11-18
theme: loop-as-infrastructure
evidence: [ef13b517c919ea76]
also: [agent-cost]
---
Before launching Claude Docs, Anthropic left one Claude Code session running for two weeks against a production-mirror staging cluster at over a million synthetic docs a day. It picked a scenario, ran the harness, read the telemetry through the Datadog MCP, shipped fixes to staging, and repeated, usually with about 11 sub-agents and 30 at peak. Changes that were hard to undo, such as schema or storage layout, waited for human approval.

At launch the service handled **4.6M docs and 2B requests with 60 server errors** on about 50 pods. The loop used about **$125,000** of inference at list price (vendor-reported). The author estimates $3,000-10,000 for a smaller service. The enabler was legibility: per-query telemetry and runtimes without garbage collection, so each metric traced back to code the team wrote.
