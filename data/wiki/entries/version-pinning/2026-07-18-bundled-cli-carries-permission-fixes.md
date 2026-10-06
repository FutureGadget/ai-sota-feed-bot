---
title: "A \"bundled CLI update\" SDK release carried a batch of permission-check fixes"
date: 2026-07-18
theme: transitive-pinning
evidence: [fc682cd69e9ef51b, fe9e50bf2d5b21fe, 6ffc451084feba44]
---
`claude-agent-sdk` 0.2.122's only listed change is a bundled CLI bump to **2.1.214**. That CLI fixed several permission checks: a **Windows PowerShell 5.1 bypass**, Bash redirect forms that now fail closed, commands over 10,000 characters that now always prompt, and `dir/**` allow rules that auto-approved nested writes. SDK 0.2.125 again forwarded only a CLI bump, to 2.1.217.

A lockfile that pins only the SDK version silently accepts, or silently misses, security-relevant behavior changes. Chain-deep pinning is a standing requirement every release repeats, not a one-off fix.
