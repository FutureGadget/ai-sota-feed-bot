---
title: "SonarQube plugins run trusted static analysis over code from Claude Code, Copilot, Codex, and Cursor"
date: 2026-07-03
theme: guardrails-and-verification
evidence: [7a882200fe85650f]
---
SonarQube now ships plugins that apply its **static analysis to code written by coding agents**, including Claude Code, Copilot, Codex, and Cursor.

It adds an independent, non-model check on what the sandbox lets an agent produce: a control on the agent's output, complementing controls on its execution and credentials.
