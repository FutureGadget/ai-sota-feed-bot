---
title: "Cloudflare AI Search runs crawl, parse, embed, and retrieve as one hosted service with an MCP endpoint"
date: 2026-09-01
theme: retrieval-architecture
evidence: [55636c14f8cd3609]
---
Cloudflare AI Search provides a ready-made search engine over custom data: crawl, parse, embed, and retrieve behind **one search endpoint**, with multimodal search, a "discover" mode that indexes pages without a sitemap, and public `/mcp` and `/search` endpoints agents can query directly.

It is the gateway pattern as a managed service: faster setup, less control over chunking, embedding, and ranking than a self-hosted stack.
