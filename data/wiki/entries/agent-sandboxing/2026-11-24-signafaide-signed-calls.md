---
title: "SignafAIde signs every agent tool call and blocks risky ones unless an independent witness allows them"
date: 2026-11-24
theme: local-sandboxes
evidence: [4abdfe0105a17f30]
also: [tool-use]
---
*SignafAIde* is an Apache-2.0 SDK (Python, TypeScript, MCP, LangChain, OpenTelemetry) that signs each tool call with the agent's key and chains the records locally, so an auditor can verify them offline. Risky calls such as pay, delete, send, or push run only when an independent witness service allows them under published rules. Recording works with no account; blocking needs the witness.

For builders: this splits the tool-call supervisor into a local tamper-evident log and an external approver. It is useful when you need to prove to a third party what an agent did, not just stop it.
