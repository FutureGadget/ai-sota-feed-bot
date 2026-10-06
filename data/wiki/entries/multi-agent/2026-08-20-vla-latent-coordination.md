---
title: "Agents can coordinate through hidden states that no transcript or span records"
date: 2026-08-20
theme: oversight-and-safety
evidence: [0ada5d894838d46e]
also: [agent-tracing]
---
Verifiable Latent Alignments (VLA) starts from the premise that agents can communicate through **continuous hidden states invisible in public transcripts**, a channel for covert coordination. For every monitored decision, VLA links the private latent-state record and channel status to the resulting public action through a **shared event identifier**, enabling matched causal analysis, and adds representation anomaly detection on top.

Reading the messages between agents does not tell you what they agreed. A message-and-tool-call span schema is not a complete record of a multi-agent run; the monitoring unit sits underneath the span.
