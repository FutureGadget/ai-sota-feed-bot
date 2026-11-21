---
title: "Frowse replaces full accessibility trees with compact page summaries plus local selector lookup"
date: 2026-11-21
theme: curating-the-working-set
evidence: [226255c029778106]
also: [agent-cost]
---
Frowse is a drop-in replacement for the agent-browser CLI. Instead of returning the full accessibility tree on each snapshot, it gives the agent a **compact semantic summary**. The agent then asks for an element in natural language, and a local model resolves the exact CSS/XPath selector on CPU in **10-25 ms** with no API call.

The author reports up to **90% fewer tokens per step**, with both tools reaching identical verified answers on three workflows (author-reported, small sample). For builders: browser tool output is a prime place to trim context at the input boundary, provided the agent can still query for detail it needs.
