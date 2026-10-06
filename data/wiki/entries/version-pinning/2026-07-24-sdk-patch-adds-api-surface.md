---
title: "SDK 0.2.126 adds terminal_reason and typed model_usage on a patch bump"
date: 2026-07-24
theme: transitive-pinning
evidence: [a19f1341e900df0e]
---
`claude-agent-sdk` 0.2.126 added real API surface on a patch release: **`ResultMessage.terminal_reason`** reports why the query loop ended (`completed`, `max_turns`, `aborted_tools`, and others), and **`model_usage`** is now typed, with `canonicalModel` and `provider` fields for stable model identity across aliases. It also bumped the bundled CLI to 2.1.218.

Integrations that pin the SDK have to decide when to adopt behavior that exists only past an exact patch version.
