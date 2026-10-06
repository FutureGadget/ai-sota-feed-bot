---
title: "Web-search APIs differ 12x in median latency, and cold caches cost up to 37x more"
date: 2026-08-28
theme: beyond-the-engine
evidence: [c6927bdb3ec146a9]
---
Measuring nine web-search APIs under identical 10-result requests found a **12x spread in median response time** (320ms to 3.9s) and up to a **37x gap** between one provider's cached and cold response (105ms vs 3,937ms).

Most providers' caches expire in 5-60 minutes, so an agent's search calls land cold far more often than a benchmark against a warm cache suggests. Choosing a search tool is a latency decision, not only a capability one.
