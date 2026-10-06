---
title: "Four one-line SDK releases forward CLI versions carrying undisclosed security fixes"
date: 2026-08-16
theme: bundled-cli-bumps
evidence: [b4f997e1a98a7444, f6440bc45449dc28, 2b3857f60a19c4e3, 7fd901719e073499]
---
SDK v0.2.135, v0.2.136, v0.2.138, and v0.2.139 forward CLI v2.1.227, v2.1.228, v2.1.232, and v2.1.233. Per the CLI notes:

- **v2.1.227**: a crafted-command Bash bypass, invisible Unicode hiding parts of a command from approval, a workflow-sandbox escape via dynamic `import()`, and `bypassPermissions` ignoring an org's disable policy.
- **v2.1.228**: synced claude.ai skills can no longer shadow local commands or run `!` shell commands.
- **v2.1.232**: PowerShell and Git Bash symlink bypasses.
- **v2.1.233**: an NTLM credential leak via `\??\` paths.

Four waves in two months make this the dependency's normal release shape.
