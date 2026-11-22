---
title: "A coding agent committed a credential that let an attacker download Together AI's stored prompt samples"
date: 2026-11-22
theme: credential-boundary
evidence: [31dbae397b46d6b3]
---
Together AI disclosed that an **AI coding agent committed a credential** to a public GitHub repository. The key opened a private Hugging Face repo of prompt samples from MiniMax M3, GLM-5.2, and Kimi K2.6 requests made in June and July 2026. Scanning caught it and the commit was reverted, but an attacker used the key during the exposure window. They then searched the prompts for other credentials and tested them. Five were canaries from the [Dragos experiment](/topic/agent-sandboxing#2026-11-20-dragos-canary-token-provider-leaks).

The fixes are scoped or short-lived credentials, credential checks on every pull request, zero data retention by default for new accounts, and new rules for coding-agent use. For builders: a reverted commit does not revoke a key. Give agents credentials short-lived enough that a leak expires.
