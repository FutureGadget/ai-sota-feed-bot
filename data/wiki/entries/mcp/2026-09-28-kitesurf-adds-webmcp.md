---
title: "Cloudflare's Kitesurf agent browser calls site-exposed WebMCP tools instead of clicking"
date: 2026-09-28
theme: webmcp
evidence: [15939a0632edddf1]
---
Kitesurf, Cloudflare's Workers-based browser for agents, now supports **WebMCP**, so an agent can call tools a site exposes (Cloudflare Radar's `navigate-to`, `set-location`) instead of simulating clicks. It also reports **730,000+ Web Platform subtests** passing, about 500,000 more than at its August launch.

Both sides of WebMCP, the page that exposes tools and the agent browser that calls them, now ship from one vendor.
