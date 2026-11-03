---
title: "Tool updates bypass in-context defenses: ETUDE reaches 97.6% attack success"
date: 2026-11-03
theme: injection-paths
evidence: [3b426192f1bc75ae]
also: [tool-use]
---
ETUDE ships malicious code in an update to an initially benign tool. The code runs outside the model's context, uses no adversarial prompt, and keeps the tool's legitimate behavior. Across seven frameworks, including Gemini CLI, Codex CLI and Claude Code, the paper reports a 97.6% attack success rate with 95.9% legitimate task completion. Existing defenses gave insufficient protection.

This is a supply-chain gap, not a prompt-injection variant. Trust granted to a tool does not survive its next version. Pin tool versions, re-verify on update, and sandbox tool execution regardless of model-side filters.
