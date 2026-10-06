---
title: "Agent SDK patch releases that only bump a bundled CLI still change what you run"
date: 2026-06-21
theme: transitive-pinning
evidence: [0971e4ffff50b51c, c69cda5ccda84a51]
---
`claude-agent-sdk` 0.2.106 and 0.2.110 each list one change: the **bundled Claude CLI** moved to 2.1.185 and then 2.1.191.

Pinning your direct dependency is not enough when it vendors an executable. The version you actually run moves at a patch bump, so the pin has to reach the whole chain: SDK, bundled CLI, and model.
