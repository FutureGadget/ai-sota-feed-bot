---
title: "GPT-6 prompt caching adds explicit breakpoints and a hit-rate dashboard"
date: 2026-09-23
theme: caching-and-serving
evidence: [f9027d80e820682e]
---
OpenAI overhauled prompt caching for GPT-6: **higher cache hit rates, a dashboard with hit-rate diagnostics, and explicit cache breakpoints** that let a team control what stays cached instead of relying on an opaque default.

Explicit breakpoints and diagnostics turn caching from a hope into something a team can engineer and monitor, which matters most for agent loops that re-send a large stable prefix every turn.
