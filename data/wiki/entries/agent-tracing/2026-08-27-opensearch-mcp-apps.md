---
title: "OpenSearch MCP Apps render trace and log visualizations inline in the agent chat"
date: 2026-08-27
theme: diagnosis
evidence: [ec596dac47b8163f]
---
Amazon OpenSearch Service's **MCP Apps** return interactive visualizations alongside an agent's text response, from one locally run MCP server. An alert investigation (trace lookup, log-pattern clustering, distributed-trace analysis, RED metrics, service-dependency mapping) happens in one IDE chat thread.

The visualization renders the **actual OpenSearch query result, not a model-generated chart**. An engineer can verify each step the agent claims without re-running the query in a separate dashboard.
