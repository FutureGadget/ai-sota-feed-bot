---
title: "TraceLab profiles real coding-agent traffic so servers can be tuned to it"
date: 2026-06-30
theme: agent-traffic
evidence: [0ca61ed96ddd38e5, d3e345ae085932a6]
---
TraceLab (University of Washington) characterizes real, day-to-day coding-agent usage across multiple agents and model families for serving-system research. Existing public traces and benchmarks don't capture that usage.

The premise: **agent workloads don't look like chat**. Coding agents issue bursty, long-context, tool-interleaved requests, so a server tuned on a generic chat trace is tuned for the wrong shape.
