---
title: "Azure AI Gateway goes GA as its own service, with enforced per-agent budgets across providers"
date: 2026-11-28
theme: vendor-spend-controls
evidence: [15de6fd5593144e3]
also: [mcp]
---
Microsoft moved Azure AI Gateway out of API Management into a standalone service, three months after the preview tier. It fronts Foundry, Azure OpenAI, OpenAI, Anthropic, Bedrock, Vertex AI, and any OpenAI-compatible endpoint, with priority, weight, or condition-based routing and failover. It also federates MCP servers and turns OpenAPI specs into MCP tools.

Tokens and estimated cost are tracked by user, team, app, agent, and provider. **Enforced budgets stop new requests** once estimated spend hits the limit. Pricing is 10,000 free requests a month. Billing starts January 1, 2027 at **$500 per gateway per month** for 10M requests, plus $20 per extra million. Private Link and tool-call threat protection are still in preview.

For builders: the cap acts on an estimate, so reconcile it against the invoice.
