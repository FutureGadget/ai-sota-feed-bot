---
title: "A score threshold decides whether code, the model, or one or two humans approve each payout"
date: 2026-11-15
theme: deterministic-boundaries
evidence: [28f36f8699e8d2c7]
---
A reference human-in-the-loop Slackbot screens marketplace payouts against a sanctions list. The name-similarity score, not the model, picks who decides:

- **Below 0.82**: plain code clears it; the model is never called.
- **0.82-0.90**: the model may clear it, only with a confident "no match" and **$500 or less**.
- **0.90-0.95**: one reviewer; the model's reasoning is shown but cannot clear.
- **0.95+**: two different reviewers; no model call.

Each saga step reads a queued message, does the work, and writes the new status plus the next message in **one Postgres transaction**. An unanswered review expires and the payout stays held.

For builders: put the tiering in one ordinary function, so the model can never do more than the code allows.
