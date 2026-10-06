---
title: "GitHub's Taskflow Agent: the LLM decides, MCP tools run the fuzzer"
date: 2026-09-26
theme: beyond-tools
evidence: [2690558920b683f4]
---
GitHub Security Lab's fuzzing taskflow for C/C++ splits the work cleanly: **"the LLM agent owns the decisions, and the MCP tools own the execution."** MCP tools run AFL with growing time budgets, compile harnesses, and store crashes. The model reads coverage reports and decides whether to add seeds, edit a harness, enrich a dictionary, or skip a plateaued path.

Structure-aware mechanisms (format dictionaries, source-extracted dictionaries, dynamic enrichment, corpus splicing) give the agent enough signal to reason about input formats. MCP acts as a pure execution boundary.
