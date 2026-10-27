---
title: "Shared KV cache leaked other tenants' prompts on Workers AI for 13 days"
date: 2026-10-27
theme: caching-and-serving
evidence: [89893d5f73c77515]
also: [agent-sandboxing]
---
Cloudflare reports a tenant-isolation bug in its GLM-5.3 Workers AI deployment (vendor-reported). From August 27 to September 9, 2026, 155 responses contained data from other customers' recent requests to the same model. A security researcher flagged it on September 8, and Cloudflare restored the model on September 9 after remediating with SGLang. No other hosted model was affected.

Takeaway: cross-request cache reuse is a security boundary, not just a cost lever. Before enabling prefix or KV sharing on multi-tenant serving, test that a cache hit never crosses tenants.
