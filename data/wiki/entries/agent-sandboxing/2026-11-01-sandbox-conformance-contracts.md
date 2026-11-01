---
title: "Open conformance lab turns sandbox claims into runnable contracts"
date: 2026-11-01
theme: local-sandboxes
evidence: [21bd8061ad22e39b]
---
The `sandbox-conformance` repository converts claims such as "the agent can't read your keys", "it can't reach the network", and "it can't plant a git hook" into contracts anyone can run. It stores per-sandbox results with evidence attached, so different coding-agent sandboxes are compared on identical tests. It is tied to no single sandbox; you add a contract, measure yours, and publish.

For builders: this is a single-author project, so treat its results as a starting checklist. Running the same contracts against your own sandbox before relying on a vendor's isolation claims is the useful part.
