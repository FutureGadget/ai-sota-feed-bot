---
title: "Claude Code makes Manual the default permission mode across CLI and IDEs"
date: 2026-07-03
theme: permission-policy
evidence: [f9a1870648a6375a]
---
Claude Code v2.1.200 changed the **default permission mode to "Manual"** across the CLI, `--help`, VS Code, and JetBrains, and stopped AskUserQuestion dialogs from auto-continuing by default.

Least privilege becomes the out-of-the-box behavior rather than an opt-in a team has to discover. Looser modes now take a deliberate choice.
