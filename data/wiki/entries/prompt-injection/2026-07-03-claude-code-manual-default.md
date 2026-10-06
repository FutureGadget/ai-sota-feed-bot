---
title: "Claude Code makes Manual its default permission mode and stops auto-continuing questions"
date: 2026-07-03
theme: harness-controls
evidence: [f9a1870648a6375a]
---
Claude Code v2.1.200 changes the default permission mode to **Manual** across the CLI, VS Code, and JetBrains, and stops `AskUserQuestion` dialogs from auto-continuing; an idle timeout is now opt-in.

Least privilege ships as the default instead of an opt-in setting. Many successful injections exploit the gap between what a default configuration permits and what the user meant to allow.
