---
title: "Framer's harness runs agent-written code as it streams, cutting tool steps 2x"
date: 2026-11-08
theme: code-driven
evidence: [c430d9570f8f07c3]
also: [agent-cost]
---
Framer replaced a per-edit DSL harness with one where the agent writes a JavaScript program that inspects the document tree and applies hundreds of changes without returning to the model for each decision. The runtime compiles incoming code into cells and executes them while the model is still generating, so edits show on the canvas early.

When an early cell fails an assumption, the stream is stopped, which avoids the remaining output-token charges, and the error goes back for a retry. Framer reports, as vendor-reported averages, 2x fewer tool steps and 39% fewer cached input tokens per message, with no measured quality loss, and up to 33% lower cost and 20% lower latency.

For builders: streaming execution makes fail-fast a cost control.
