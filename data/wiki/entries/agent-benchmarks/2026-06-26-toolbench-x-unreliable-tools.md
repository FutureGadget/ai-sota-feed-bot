---
title: "ToolBench-X scores agents when tools time out, error, or return malformed results"
date: 2026-06-26
theme: adversarial-and-security
evidence: [ebc3627096b332c8]
---
"Beyond Function Calling" introduces **ToolBench-X**, which tests agents under recoverable reliability hazards: tools that time out, error, or return malformed results, across sequential, parallel, and mixed workflows with deterministic tools.

It exposes agents that pass clean tool suites but cannot recover when the environment misbehaves. The benchmark targets the **failure-recovery path**, not the happy path.
