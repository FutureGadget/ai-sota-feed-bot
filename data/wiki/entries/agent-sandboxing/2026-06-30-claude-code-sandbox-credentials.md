---
title: "Claude Code's sandbox.credentials blocks sandboxed commands from reading secrets"
date: 2026-06-30
theme: credential-boundary
evidence: [0d10a691ebcb0e61]
---
Claude Code v2.1.187 added a **`sandbox.credentials` setting** that stops sandboxed commands from reading credential files and secret environment variables. The same release added org-configured model restrictions.

It closes part of the "the box still holds tokens" gap at the harness-config layer, with no change to the agent's code.
