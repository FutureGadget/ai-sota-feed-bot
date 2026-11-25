---
title: "Cloudflare turns site search for agents into a toggle: auto-indexed, discoverable on the site's own domain"
date: 2026-11-25
theme: agent-native-surfaces
evidence: [48919c55052d9c92]
also: [grounding]
---
**Search for Agents** creates an AI Search instance for a Cloudflare zone, indexes its content, and exposes a discoverable search API on the site's own domain, with HTTP `QUERY` support. It follows *Markdown for Agents*, which converts HTML to Markdown via content negotiation at the edge. It is available on all plans, including Free with limits.

For builders: sites are starting to publish their own retrieval endpoints. An agent that queries a site's search API instead of crawling pages gets fresher, scoped results for fewer tokens.
