---
title: "A static verifier checks OpenCode tool calls against safety properties before they run"
date: 2026-07-27
theme: guarding-the-call
evidence: [2e3ad0e505f55b80]
---
A Show HN plugin brings the formal-verification work in "Guardians of the Agents" (Erik Meijer; implemented by Nada Amin) to OpenCode. It hooks `tool.execute.before` to intercept candidate `bash`, `read`, `edit`, and `write` calls and **verifies them statically before execution**.

It is a pre-execution check, complementary to sandboxing and authorization, which limit what happens after a call runs. See [agent sandboxing](/topic/agent-sandboxing).
