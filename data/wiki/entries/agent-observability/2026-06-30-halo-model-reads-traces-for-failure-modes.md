---
title: "HALO runs a model over agent traces to find recurring harness-level failure modes"
date: 2026-06-30
theme: reading-traces
evidence: [5d7159ca706a44c0]
---
**HALO** is an open-source local debugger that ingests Langfuse, Arize/OpenInference, or JSONL traces and uses an RLM-based engine to find **recurring harness-level failure modes**. It produces reports you can feed into Cursor or Claude Code to patch the agent, and a desktop app answers questions over the traces.

The engineer stops reading every span: a model reads the traces and the human reviews the patterns.
