---
title: "Permission Slips lets only a human-typed prompt issue scoped, expiring grants for risky agent actions"
date: 2026-11-27
theme: permission-policy
evidence: [155371850eeda6e4]
also: [prompt-injection]
---
Permission Slips adds two hooks to Claude Code and Codex. A `UserPromptSubmit` hook records a slip such as `/slip deploy api` only when the human types it, so the model never writes the ledger. A `PreToolUse` hook matches each call against regex rules and denies a risky one that no valid slip covers. Slips name a target and a lifetime (`once`, `prompt`, `session`, `until-spent`). The README limits the claim to agents drifting past intent, not hostile ones. An agent with shell access could still reach the ledger unless it lives outside writable paths.

For builders: tie authority for destructive actions to the human input channel, not to text the model can produce.
