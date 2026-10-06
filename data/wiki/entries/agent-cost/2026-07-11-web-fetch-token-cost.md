---
title: "One Wikipedia page is 68,240 raw-HTML tokens; a failed fetch pays the full bill"
date: 2026-07-11
theme: harness-and-context
evidence: [c74bb13bcd038d10]
---
A practitioner measured page costs in Claude Code research sessions: an average Wikipedia article is **68,240 tokens of raw HTML** (Nike's homepage is 353,000), against about 950 tokens once the web-fetch tool summarizes it.

The cheap path can invert. On JS-rendered or anti-bot pages the fetch returns nothing useful and the agent dumps the raw HTML into context anyway, **paying the worst-case bill for a failed read**. Fetched content is its own cost line and needs its own guard.
