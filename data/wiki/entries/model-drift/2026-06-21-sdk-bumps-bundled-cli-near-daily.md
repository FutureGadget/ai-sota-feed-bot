---
title: "Claude Agent SDK releases often consist only of a bundled-CLI bump"
date: 2026-06-21
theme: bundled-cli-bumps
evidence: [0971e4ffff50b51c, c69cda5ccda84a51, f133907eceb910d7]
---
claude-agent-sdk-python v0.2.106 and v0.2.110 each list a single change: **"Updated bundled Claude CLI"**, to 2.1.185 and 2.1.191. One CLI release in that span, v2.1.190, describes itself only as "Bug fixes and reliability improvements".

A patch-level SDK bump swaps the executable your agent runs on, and neither changelog says what behavior moved. Treat the bundled CLI version as a dependency you track separately.
