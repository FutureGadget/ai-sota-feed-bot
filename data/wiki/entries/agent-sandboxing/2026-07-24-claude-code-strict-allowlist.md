---
title: "Claude Code's strictAllowlist denies non-allowlisted hosts without prompting"
date: 2026-07-24
theme: egress-and-escapes
evidence: [228dddec5b6b8ab4]
---
Claude Code v2.1.219 added **`sandbox.network.strictAllowlist`**, which denies non-allowlisted hosts for sandboxed commands **without asking**.

Network egress moves from allow-with-a-prompt to default-deny. Prompted egress relies on a human catching the bad host; default-deny does not.
