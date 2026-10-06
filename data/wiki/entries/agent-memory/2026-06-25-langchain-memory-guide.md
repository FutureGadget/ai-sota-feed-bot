---
title: "LangChain's memory guide adds trace analysis on top of the short-term/long-term split"
date: 2026-06-25
theme: architectures
evidence: [a44d7493026627ec]
---
LangChain's practical guide to agent memory lays out **short-term and long-term memory** as settled practice, then adds a feedback loop: analyze the agent's own traces in LangSmith to decide what is worth remembering and to improve across runs.

Memory becomes something the agent curates from its own history, not just a place facts get dumped.
