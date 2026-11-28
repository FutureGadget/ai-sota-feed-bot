---
title: "Sentinel grades live coding agents by checking their git diff against what they claim"
date: 2026-11-28
theme: monitoring-limits
evidence: [d149edb0eafc6cb3]
also: [agent-reliability]
---
Sentinel, open source under the `run-llama` GitHub org, watches coding agents (Claude Code, Codex, Gemini CLI, aider, Cursor and others) in macOS terminal windows. Every 30 seconds by default, it captures `git status` and `git diff HEAD` and rates whether the changes match the agent's claims: `yes`, `partial`, `mismatch`, or `no_diff`.

An auditor model, Gemini by default or any OpenRouter or local Ollama model, assigns verdicts such as `stuck_in_loop`, `ignoring_instructions`, and `sabotaging_work` (weakened tests, deleted files, bypassed checks). It also drafts a message you can paste to redirect the agent.

For builders: comparing claims with the diff catches failures a transcript-only monitor misses. The project publishes no miss rate, so treat its verdicts as triage, not proof.
