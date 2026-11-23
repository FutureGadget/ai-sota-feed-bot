---
title: "Slipmark binds each agent sign-off to SHA-256 hashes of the files it read and fails CI on change"
date: 2026-11-23
theme: verifying-the-work
evidence: [b5f0a68bb81481a9]
---
Slipmark has a coding agent record its verdict with `slipmark attest`, which stores a SHA-256 of every file the review read. A GitHub Action refuses to ship when any attested file changed after sign-off, so a review cannot silently cover code that was edited later. It makes no model calls and needs no account.

For builders: this turns "the agent reviewed it" from a chat claim into a checkable artifact. It proves which bytes were read, not that the review was correct.
