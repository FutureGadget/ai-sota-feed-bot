---
title: "Foglamp instruments an agent's LLM calls without config or code changes"
date: 2026-07-04
theme: capture
evidence: [b71a53d3b8d39831]
---
Foglamp has the agent auto-detect its own LLM calls and instrument them **without the developer touching config or code**, then shows cost per call, latency, and quality/eval scores on a dashboard.

Capture is commoditizing into a drop-in. The decision that remains is where those traces land and in what format, because that is what decides lock-in.
