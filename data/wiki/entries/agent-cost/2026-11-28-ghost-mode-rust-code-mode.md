---
title: "Ghost Mode brings Code Mode to Rust agents with an in-process interpreter and two tools"
date: 2026-11-28
theme: harness-and-context
evidence: [3300cef8bc936b17]
also: [tool-use]
---
Ghost Mode is an MIT-licensed Rust crate. The model gets two definitions, `execute` and `poll`, and writes a short Python script that chains your tools or an MCP server's tools. The script runs in the Monty interpreter inside your process, so intermediate results never return to the model. The author reports a **~60% token cut** on their own agent.

The README is candid about limits. In-process Monty is not crash-isolated, so untrusted scripts need the `monty-pool` worker-process backend. Per-result `Limits` (40,000 characters by default) cap what any one result can add. In a cited eight-model benchmark, weaker models retried failing scripts until some runs cost more than plain tool calls.

For builders: Code Mode is no longer TypeScript-only. Measure retries per model before you switch.
