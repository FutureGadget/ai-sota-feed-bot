---
title: "Remembrane makes agent recall deterministic enough to unit-test in CI"
date: 2026-08-09
theme: local-first-stores
evidence: [6e834d3516003b88]
---
**Remembrane** keeps agent memory in one SQLite file with zero dependencies in the default install. Its author built it because a few thousand short strings didn't justify a hosted API, a vector database, or a framework.

The distinctive part: **recall is deterministic**, so you can write unit tests that assert what the agent remembers and run them in CI. Memory becomes something you can regression-test, not just observe.
