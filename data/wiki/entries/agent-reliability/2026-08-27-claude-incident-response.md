---
title: "In incident response, Claude excels at reading logs and fails at causation"
date: 2026-08-27
theme: consistency-and-autonomy
evidence: [5cfa494a315266ad]
---
Anthropic reliability engineer Alex Palcuie reports on using Claude for incident response:

- **Observe works.** It flagged 4,000 accounts created at once with identical traits as coordinated fraud, and root-caused a Rust panic in `checkpoint.rs` before engineers finished reading the logs.
- **Orient breaks.** Seeing requests and errors double together, it repeatedly called a capacity problem when a failed KV cache was the cause; the engineer corrected it "six, seven times" before adding the distinction to the system prompt.
- Postmortems come out "80% readable" but miss contributing factors.

The open risk: if AI runs mitigation, humans lose the feedback loop that builds senior-responder judgment.
