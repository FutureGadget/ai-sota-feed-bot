---
title: "Lockward pins the skills, MCP servers, hooks, and rules files agents load, and fails CI on unapproved changes"
date: 2026-11-26
theme: transitive-pinning
evidence: [654618872ac83495]
also: [prompt-injection]
---
Lockward treats an agent's configuration as a supply chain. It records every skill, MCP server, hook, rules file, and security-relevant setting used by Claude Code, Cursor, Codex, Gemini CLI, Windsurf, and GitHub Copilot. When any of them changes without approval, it fails locally or in CI. It runs offline, needs no account, uses no LLM, and emits SARIF and CycloneDX AI-BOMs.

For builders: a silently updated skill or MCP server changes agent behavior as much as a dependency bump. Pin those files the way you pin packages, and route changes through review.
