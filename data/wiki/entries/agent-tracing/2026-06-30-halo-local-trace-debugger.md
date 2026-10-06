---
title: "HALO runs a model over trace corpora to find recurring harness failures"
date: 2026-06-30
theme: diagnosis
evidence: [5d7159ca706a44c0]
---
HALO is an open-source, local tool that ingests **Langfuse, Arize/OpenInference, or JSONL traces** and uses an RLM-based engine to find recurring harness-level failure modes across runs. It writes reports you can hand to Cursor or Claude Code to patch the agent, and its desktop app answers questions over your traces.

The trace becomes the input to a diagnosis loop, not just an audit log. Because it reads open trace formats, the analyzer stays swappable.
