---
title: "Memharness puts bi-temporal agent memory in one SQLite file"
date: 2026-06-20
theme: local-first-stores
evidence: [623de2bad771dca8]
---
**Memharness** stores agent memory bi-temporally in a single SQLite file: it tracks both **when a fact was true and when the agent learned it**.

That lets recall reason about staleness instead of returning whatever embeds nearest. Richer temporal modeling is a recurring design choice in the local-first stores.
