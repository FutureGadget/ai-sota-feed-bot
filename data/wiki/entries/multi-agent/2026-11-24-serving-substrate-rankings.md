---
title: "Multi-agent topology rankings flip with the serving stack: Star fell from first to fourth under KV pressure"
date: 2026-11-24
theme: when-it-pays
evidence: [9ef53558a95bc11c]
also: [agent-latency, agent-benchmarks]
---
*MASSys* runs the same multi-agent workflows, with fixed models and prompts, across serving substrates and load levels in five task families. Under KV-cache pressure, the Star topology dropped from **first to fourth** in mean latency while Chain rose from fourth to first. Higher load produced long runtime tails and timeouts, so the system delivered fewer usable results even when the outputs that finished stayed competitive.

For builders: a topology comparison is only valid for the serving setup it ran on. Benchmark candidate designs on your own inference stack at production load, and count timed-out jobs against quality.
