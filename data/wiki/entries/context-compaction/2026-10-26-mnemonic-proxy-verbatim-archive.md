---
title: "A transparent proxy keeps full agent history in an archive and sends only a 32K window"
date: 2026-10-26
theme: skipping-compaction
evidence: [aec1f0ba52ad6990]
also: [agent-memory]
---
`mnemonic-proxy` sits between a coding agent and an OpenAI-compatible local model server such as llama.cpp. The agent keeps sending its whole unmodified history; the proxy decides what the model reads. Old material leaves the prompt but is archived verbatim and recalled in structured form, never summarized away. The README claims it beat full context on long agent histories at a 32K window (project-reported, single repository).

For builders: this moves compaction out of the agent loop, so the harness needs no changes and nothing is lost irreversibly.
