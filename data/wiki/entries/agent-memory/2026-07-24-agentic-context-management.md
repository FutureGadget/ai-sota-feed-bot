---
title: "Agentic Context Management treats memory as a lifecycle, not a store"
date: 2026-07-24
theme: architectures
evidence: [fae52c3b17c1c504]
also: [agent-cost]
---
The ACM paper argues production agents fail less from weak reasoning than from unmanaged context: histories, large prompts, tool definitions, and ballooning tool outputs. It names five primitives (**architecting, ingesting, scoping, anticipating, compacting and consolidation**) and ships a reference implementation, Maximem Synap.

It puts a shape on the cost curve: naive accumulation grows token cost quadratically with conversation length, crude summarization buys linear cost with an accuracy cliff, and only validated compaction gets linear cost with fidelity preserved. See [context compaction](/topic/context-compaction).
