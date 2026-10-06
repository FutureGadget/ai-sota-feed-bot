---
title: "Metered APIs and agents should ship hard budget caps on by default"
date: 2026-10-05
theme: hard-caps
evidence: [47be91cd52d348eb, cff5d80a676b706a]
also: [agent-cost]
---
Simon Willison argues that pay-by-usage services and APIs need **default hard budget caps**: "after $X/month, cut this thing off," not an alert that arrives after the bill. Agents can burn metered usage faster than a human notices.

A Pi-based coding agent shown on Hacker News ships the same limit inside the agent itself, with hard budget caps as a product feature.

Both treat the cap as the backstop under visibility and alerts. The open design question is the default: off until configured, or on until raised.
