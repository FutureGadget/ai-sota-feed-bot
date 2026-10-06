---
title: "Only validated compaction gets linear cost without an accuracy cliff, says ACM"
date: 2026-07-24
theme: harness-and-context
evidence: [fae52c3b17c1c504]
---
"Agentic Context Management" (ACM) argues production agents fail less from weak reasoning than from unmanaged context: histories, large prompts, tool definitions, ballooning tool outputs. It frames three regimes:

- **Naive accumulation:** per-step cost grows quadratically with conversation length.
- **Crude summarization:** linear cost, but an accuracy cliff.
- **Validated compaction:** linear cost with fidelity preserved.

Its reference implementation is Maximem Synap. Treat memory and cost as one lifecycle problem; see [context compaction](/topic/context-compaction).
