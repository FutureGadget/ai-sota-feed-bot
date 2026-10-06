---
title: "Server-side gates check a tool call after the model decides but before the request is sent"
date: 2026-07-15
theme: deterministic-boundaries
evidence: [e057b58674d089fa]
---
Quickchat's write-up on reliable agent actions describes two mechanisms. A **server-side gate** evaluates conditions after the model decides to call a tool but before the request goes out, so a prompt-injected model cannot talk its way past the check. A **JSONPath extraction step** stores values from earlier API responses so later steps reference a saved field instead of the model re-typing, and possibly hallucinating, an ID.

Enforcement lives outside the model's decision, not inside a longer, more careful prompt.
