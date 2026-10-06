---
title: "A cosmetic-looking SDK bump rode on a CLI fixing a zsh permission bypass"
date: 2026-08-07
theme: bundled-cli-bumps
evidence: [ba2a3cbea388e94b, b52989abd31085bd, 1be544292b970eeb]
---
SDK v0.2.130 and v0.2.131 again read only "Updated bundled Claude CLI" (to v2.1.222, then v2.1.223). The CLI release just before them, **v2.1.221**, fixes a Bash permission-check bypass where zsh could run hidden commands inside `[[ ]]` regex conditionals, and a Windows PowerShell check mishandling quoted paths.

It also adds `mode: "mask"` for sandbox credential files: sandboxed commands read a sentinel copy while the sandbox proxy substitutes the real value on egress. On macOS, masking falls back to deny.
