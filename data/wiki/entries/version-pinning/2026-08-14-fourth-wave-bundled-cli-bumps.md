---
title: "Four more \"bundled CLI only\" SDK releases forward CLI changes in four days"
date: 2026-08-14
theme: transitive-pinning
evidence: [b4f997e1a98a7444, f6440bc45449dc28, 2b3857f60a19c4e3, 7fd901719e073499, b56da077d21ad4f4]
---
`claude-agent-sdk` 0.2.135, 0.2.136, 0.2.138, and 0.2.139 each list only a bundled CLI update, to **2.1.227, 2.1.228, 2.1.232, and 2.1.233**. The forwarded CLIs are not cosmetic: 2.1.233, for example, closes a path-validation bypass for Windows paths using the NT `\??\` device prefix.

A version-only SDK pin cannot tell "safe to skip" from "actually changed". Read the bundled CLI's changelog on every SDK bump, or pin the CLI explicitly.
