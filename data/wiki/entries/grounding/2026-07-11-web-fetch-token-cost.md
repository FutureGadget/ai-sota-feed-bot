---
title: "A raw Wikipedia page costs an agent 68,240 tokens before it can ground on anything"
date: 2026-07-11
theme: context-budget
evidence: [c74bb13bcd038d10]
---
A Claude Code user measured page costs: an average Wikipedia article is **68,240 tokens of raw HTML** and Nike's homepage 353,000. Claude Code's WebFetch summarizes Wikipedia to about 950 tokens, but returns nothing on JS-rendered and some anti-bot pages, and the agent then dumps raw HTML into context. A stealth-browser fetch tool that converts to markdown brings the page to roughly 3,000-5,000 tokens.

Most of the raw page is boilerplate the model must read before reaching the relevant part. Budget the fetch layer, not just the model call. See [agent cost](/topic/agent-cost).
