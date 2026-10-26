---
title: "A planted AGENTS.md in Downloads hijacked coding agents into installing malware"
date: 2026-10-26
theme: injection-paths
evidence: [264cc0e36820b485, e8085371baf80a90]
also: [agent-sandboxing]
---
Forever Security caught live malware that dropped a malicious `AGENTS.md` into a customer's Downloads folder. The agent read it as trusted project instructions and installed a rogue npm package; against OpenAI Codex this was reproduced, and a related technique against Claude Code leaked OAuth tokens (researcher-reported).

The mechanism is ordinary: instruction files are loaded automatically, so any file that lands where the agent looks is a command channel, with no prompt for the user to review.

For builders: treat instruction files as untrusted input unless they come from the repository itself, scope where the harness searches for them, and gate package installs behind approval.
