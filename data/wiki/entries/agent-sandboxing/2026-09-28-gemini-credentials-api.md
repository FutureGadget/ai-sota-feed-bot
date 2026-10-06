---
title: "Gemini Managed Agents' Credentials API makes egress-proxy secret injection a platform primitive"
date: 2026-09-28
theme: credential-boundary
evidence: [b7d482ff6a323e55]
---
Google generalizes token substitution into a first-party API:

- A secret is stored once, write-only and encrypted at rest, as a `bearer_token`, `oauth2` (with automatic refresh), or `environment_variable`.
- It is referenced by ID from a remote MCP tool, a network-allowlist domain, or a sandbox env var.
- The container sees only a placeholder (`__GEMINI_CRED_<id>__`); the egress proxy injects the real value **only for that credential's `trusted_domains`**.

A dependency that reads `os.environ` leaks nothing usable.
