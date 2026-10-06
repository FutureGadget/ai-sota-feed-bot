---
title: "Agents that pass clean tool suites degrade sharply when tools time out or return bad data"
date: 2026-06-26
theme: calling-reliability
evidence: [ebc3627096b332c8]
---
"Beyond Function Calling" introduces **ToolBench-X**, a benchmark for tool-environment unreliability: tools that time out, error, or return malformed or inconsistent results. Agents that look competent on clean, stable tool suites degrade sharply once the environment misbehaves.

A passing schema test is no evidence the agent recovers when the tool itself fails. Test tool-failure handling the way you would test any client of a flaky dependency.
