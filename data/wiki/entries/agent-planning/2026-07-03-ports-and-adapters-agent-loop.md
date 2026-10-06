---
title: "A provider-agnostic agent loop built on ports and adapters"
date: 2026-07-03
theme: loop-as-infrastructure
evidence: [9ae3d20f85fa904c]
---
An engineer at Featherless kept rebuilding the same loop (call model, run tools, feed results back, stop), so he extracted it and put **every piece behind an interface**. The MIT-licensed result works with any OpenAI-compatible endpoint and does not own the UI or control flow.

The loop itself becomes portable infrastructure, separable from any one framework or provider.
