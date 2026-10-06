---
title: "Azure Functions folds the tool-calling loop into a serverless agents runtime"
date: 2026-06-20
theme: production-runtimes
evidence: [4f7d4f99793e131d]
also: [mcp]
---
Azure Functions shipped a serverless agents runtime in public preview at Build 2026. An agent is an `.agent.md` file with **YAML triggers, MCP server access, 1,400+ connectors, and sandboxed execution**. The Functions team told InfoQ the runtime adds no cold-start overhead and no billing premium beyond standard Flex Consumption (vendor-reported).

MCP access becomes a default runtime feature rather than something each team wires in, and the cloud platform takes over hosting the tool loop.
