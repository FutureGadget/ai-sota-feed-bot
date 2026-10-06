---
title: "Production agent failures come from the harness, and four invariants address them"
date: 2026-09-21
theme: deterministic-boundaries
evidence: [0a7a12052d2d17b7]
---
OpenAI's Vinoth Govindarajan argues, using incidents such as OpenClaw, that production agents fail beyond model hallucination. He places the fix in the harness:

- explicit **state ownership**
- **serialized** concurrent state mutations, so two in-flight actions cannot corrupt shared state
- execution authority **scoped per step**
- actions **validated at the user-visible edge**, not by the model's own account of what it did

Each item is an invariant a team can audit its harness against.
