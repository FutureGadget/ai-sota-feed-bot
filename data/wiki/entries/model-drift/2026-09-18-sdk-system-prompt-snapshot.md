---
title: "SDK adds system-prompt snapshots that change caching across resumed sessions"
date: 2026-09-18
theme: bundled-cli-bumps
evidence: [d0e22204dfaa8824]
---
SDK v0.2.153 adds a `snapshot` field to `SystemPromptPreset` and a new `SystemPromptCustom` typed dict. With `snapshot: True`, a session **keeps the system prompt recorded on its first request**, improving prompt caching across resumed sessions; with `False`, the prompt is rebuilt every request. It requires CLI 2.1.257+ and ships with a bump to v2.1.273.

A resumed session can now run on an older system prompt than a fresh one, which matters when comparing behavior across sessions.
