---
title: "Copilot CLI read ~/.ssh on request with no approval prompt under default settings"
date: 2026-10-30
theme: permission-policy
evidence: [445d06ae5b2fba6f]
also: [prompt-injection]
---
A developer reports (single hands-on test, not vendor-confirmed) that Copilot CLI 1.0.105 on macOS, in a fresh directory with default settings and no saved approvals, ran `ls ~` and `cat` on a canary file in `~/.ssh` without any permission dialog. The only prompt was the startup folder-trust question.

Folder trust therefore acted as blanket shell trust. Treat default agent permission modes as open to your home directory: run agents in a sandbox or container, keep credentials out of reach, and verify behavior with a canary file rather than the docs.
