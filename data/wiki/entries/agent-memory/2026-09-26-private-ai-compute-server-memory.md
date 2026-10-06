---
title: "Google puts server-side agent memory inside hardware enclaves the provider can't read"
date: 2026-09-26
theme: shared-memory
evidence: [1043d9fe80283e6f]
---
Google added private, server-side memory to **Private AI Compute**. Memory runs inside hardware-enforced secure enclaves, unlockable only with device-held keys, so context persists between sessions without the provider being able to read it.

It answers "remember across sessions without leaking" at the infrastructure layer, a privacy-by-construction guarantee rather than application-level scoping.
