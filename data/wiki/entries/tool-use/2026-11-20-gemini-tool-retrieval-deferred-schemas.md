---
title: "Gemini API Tool Retrieval loads tool schemas on demand instead of sending the whole library each call"
date: 2026-11-20
theme: discovery-and-definitions
evidence: [056cf0b58a3dbace]
also: [agent-cost]
---
Google added Tool Retrieval in preview to the Gemini Interactions API. Developers add a `tool_search` tool and set `defer_loading: true`, and the model fetches a tool's parameter schema only when it needs that tool. Google says this cuts input tokens and latency and keeps tool choice accurate as libraries grow; it published no numbers in the announcement.

This puts Gemini alongside harnesses that already search the tool catalog instead of listing every schema. For builders: a large tool library no longer forces you to pre-filter tools yourself, but tool descriptions now act as the search index, so they need the same care as the schemas.
