---
title: "A one-line SDK changelog forwarded five permission-check bypass fixes"
date: 2026-07-18
theme: bundled-cli-bumps
evidence: [fc682cd69e9ef51b, fe9e50bf2d5b21fe]
---
SDK v0.2.122 says only "Updated bundled Claude CLI", to claude-code v2.1.214. That CLI release lists **five permission-check fixes**:

- a bypass in Windows PowerShell 5.1 sessions
- file-descriptor redirect forms that now fail closed
- `dir/**` allow rules auto-approving writes outside the intended directory
- commands over 10,000 characters now always prompting
- zsh variable subscripts misjudged by Bash checks

Security-relevant behavior changed under a dependency whose own notes gave no hint. Read the forwarded CLI's release notes on every bump.
