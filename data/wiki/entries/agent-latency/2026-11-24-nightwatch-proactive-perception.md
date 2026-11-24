---
title: "A 0.8B monitor watching the screen cut computer-use agents' non-reasoning wait time by 33%"
date: 2026-11-24
theme: beyond-the-engine
evidence: [271d24131ba5b79a]
---
*NightWatch* pairs a computer-use VLM agent with a **0.8B** monitoring model that streams interface state, so the main agent stops sleeping for fixed intervals or re-screenshotting to check whether a page has loaded. It cut non-reasoning wall-clock time by **33%** on OSWorld and raised DynaCU-Bench success from **39.5% to 44.2%**.

For builders: in computer-use agents much latency is waiting, not inference. A small, cheap watcher that signals when the interface is ready recovers that time without touching the main model.
