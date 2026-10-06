---
title: "BetterDB puts agent memory, semantic caching, and typed retrieval on one Valkey instance"
date: 2026-06-27
theme: datastores-you-run
evidence: [4532a97181f06d93]
---
BetterDB released an MIT-licensed, **Valkey-native context layer**: agent memory, semantic plus multi-tier caching, and typed retrieval packages (npm and PyPI) that run on any Valkey or Redis-compatible instance, local or hosted.

The "buy a separate vector DB" hop collapses into the cache a team already operates. Memory and caching share one substrate, so there are not two systems to keep consistent.
