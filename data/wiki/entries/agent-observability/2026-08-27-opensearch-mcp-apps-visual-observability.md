---
title: "OpenSearch MCP Apps return trace waterfalls and service maps inline in the agent chat"
date: 2026-08-27
theme: reading-traces
evidence: [ec596dac47b8163f]
---
Amazon OpenSearch Service's **MCP Apps** return an interactive visualization alongside each tool call's text response. A local MCP server authenticates with AWS credentials, queries the same OpenSearch and Prometheus sources behind existing dashboards, and renders the result inline in the IDE.

One conversation moves from alert to log clustering, trace waterfalls, and service maps without opening a separate tool. [MCP](/topic/mcp) carries the observability payload itself.
