---
title: "Johann Rehberger bypasses Claude Code Auto Mode about 80% of the time"
date: 2026-08-28
theme: harness-controls
evidence: [86c9015dd55dff65]
---
Johann Rehberger found a prompt-injection attack on Claude Code's Auto Mode with Opus 5 that succeeds **roughly 80% of the time**. It tricks the agent into extracting a ZIP archive and running a Python import that executes a malicious local `struct.py` instead of the standard-library module. After Claude noticed the compromise, Auto Mode's own classifier **blocked the cleanup command** meant to kill the malicious process.

His conclusion: run unattended agents in a sandbox with network restrictions and credential isolation, and treat Auto Mode as one layer. A sandbox bounds what a hijacked agent can do; a classifier is not a reliable judge of whether it was hijacked.
