---
title: A signed MCP tool can still leak data; fork-per-call execution bounds what it can disclose
date: 2026-11-05
theme: guarding-the-call
evidence: [1c990a2a55a59e80]
also: [mcp, agent-sandboxing]
---
A paper shows a validly signed MCP tool embedding sensitive data in requests to a policy-allowed destination. Meta's MCPGuard-Dynamic blocked a direct exfiltration attempt but missed this attack in every trial.

The proposed **germline execution** forks each tool call from a data-free process, and each copy receives only data authorised for its destination. Across 153 attack runs, no unauthorised disclosure was detected, against 5.9-74.5% under baseline defences (paper-reported).

A single copy served calls in 10-49 ms, 2-28x faster than restarting the tool per call. For builders: signatures prove who published a tool, not what it does with the data you hand it. Isolate data per call.
