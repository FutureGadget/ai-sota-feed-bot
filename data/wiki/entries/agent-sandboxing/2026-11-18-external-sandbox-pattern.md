---
title: "The external sandbox pattern keeps the agent outside and sends only its code execution in"
date: 2026-11-18
theme: local-sandboxes
evidence: [e45fd791e1fe03c2]
---
Simon Willison and Prime Radiant published an **external sandbox** pattern. The agent runs on the host and makes localhost API calls to a dedicated sandbox whenever it wants to execute code. Three implementations share one API: v86 (Alpine in WebAssembly), Apple Containers, and Microsoft's Quicksand (QEMU in a Python package). Pi, Claude Code and Codex can each be pointed at it.

Each sandbox includes an optional HTTP/HTTPS **allow-list proxy** that can be changed while running, plus **credential replacement**, so code can make authenticated calls without the agent ever holding the secret. For teams trying local models, this separates "where the agent reasons" from "where untrusted code runs" without moving the whole harness into a VM.
