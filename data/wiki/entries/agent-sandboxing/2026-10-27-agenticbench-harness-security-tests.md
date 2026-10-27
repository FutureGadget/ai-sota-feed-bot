---
title: "AgenticBench audits what 25 coding-agent harnesses do with egress, telemetry and secrets"
date: 2026-10-27
theme: guardrails-and-verification
evidence: [57978a6d1478d544]
---
AgenticBench, a Show HN project, runs 9 security tests on 25 AI coding agents. It tests the harness itself (egress, telemetry, workspace boundaries, secrets), not the security of the code the agent writes. Each test ran once per harness in a fresh container with default settings. Outcomes come from captured system-call traces, model requests and network traffic. A test a harness never exercised is not counted as a pass.

Takeaway: default settings are what ships, so audit your harness's actual egress and secret handling from traces rather than from vendor documentation. Single run per cell, so treat results as a starting point.
