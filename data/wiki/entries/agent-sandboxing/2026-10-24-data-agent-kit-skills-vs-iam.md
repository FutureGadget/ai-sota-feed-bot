---
title: "Google's Data Agent Kit splits agent guardrails between skill instructions and IAM"
date: 2026-10-24
theme: permission-policy
evidence: [3bd1cad5c88eca17]
also: [mcp]
---
Google made Data Agent Kit generally available: a free set of MCP tools and 37 open-source skills connecting coding agents to more than fifteen Google Data Cloud services. Per InfoQ, two kinds of guardrail ship with it, split between skills and IAM.

The split matters because skill text only advises the agent, while IAM is enforced by the platform regardless of what the agent does. Treat IAM roles as the hard boundary and skills as guidance.
