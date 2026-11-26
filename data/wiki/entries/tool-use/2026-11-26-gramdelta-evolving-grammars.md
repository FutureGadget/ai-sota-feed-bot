---
title: "GramDelta updates decoding masks for grammar rules added mid-generation, with 11x lower latency than replay"
date: 2026-11-26
theme: calling-reliability
evidence: [aa06bc3c1c64285e]
also: [agent-latency]
---
Constrained decoding normally assumes a fixed grammar. When an agent's output grammar grows at runtime, such as a tool schema registered mid-session, the engine must replay the committed prefix to rebuild parse state. GramDelta handles append-only rule additions incrementally, updating parse state and next-token masks without replay. The authors report **10.7-11.5x** lower median update latency.

For builders: dynamic tool catalogs and structured output do not have to trade off. Incremental grammar updates let a server add schemas mid-stream without a latency spike.
