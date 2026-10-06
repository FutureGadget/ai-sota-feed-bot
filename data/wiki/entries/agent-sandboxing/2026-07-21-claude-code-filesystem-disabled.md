---
title: "Claude Code can turn off filesystem isolation while keeping network egress control"
date: 2026-07-21
theme: egress-and-escapes
evidence: [44423c0a85b4d691]
---
Claude Code v2.1.216 added **`sandbox.filesystem.disabled`**, which skips filesystem isolation but keeps network egress control.

One bundled sandbox toggle becomes two independent controls. When a task only needs the egress boundary (stop data leaving), a team can drop the filesystem layer and its friction without giving up exfiltration protection.
