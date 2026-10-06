---
title: "Azure API Management's AI Gateway tier governs models and MCP servers in one control plane"
date: 2026-08-12
theme: auth-and-governance
evidence: [4daf9a3fc6b23a4c]
also: [tool-use]
---
Microsoft released a dedicated **AI Gateway tier** of Azure API Management in public preview. Its control plane is built around models, MCP servers, and tools rather than APIs, and it fronts Foundry, Bedrock, Vertex AI, and OpenAI behind one endpoint, with policy cards instead of XML.

Architects welcomed the consolidation but questioned where the governance boundary sits. MCP server governance now sits next to model governance in a managed product.
