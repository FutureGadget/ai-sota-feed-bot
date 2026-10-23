---
title: "Commerce.com turns on WebMCP for ~100,000 storefronts at the edge, with per-merchant opt-out"
date: 2026-10-23
theme: webmcp
evidence: [6ce711ef5d9be5fe]
---
Cloudflare and Commerce.com enabled **WebMCP** across almost 100,000 storefront domains without theme edits. An edge-injected script bridges tool definitions from the platform's backend MCP server (`/api/mcp`) into the browser, so an agent calls `search_products` and `add_to_cart` instead of clicking through variant drop-downs and cookie banners.

Merchant control is a Configuration Rule on custom-hostname metadata (`webmcp_opt_out`), evaluated before the page is served. Opted-out stores get no injected script. If the MCP server is offline or the browser lacks WebMCP, the script exits and the storefront loads normally. Checkout stays with the human.

For builders: one set of tools can serve both server-side MCP and in-browser agents. WebMCP is still an experimental Chrome-flag preview.
