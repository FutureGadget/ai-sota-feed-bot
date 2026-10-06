---
title: "Supafax uses the user's email outbox as an agent's memory and config store"
date: 2026-06-30
theme: architectures
evidence: [ee624f89c3319a44]
---
Supafax is an agent that **uses email as its memory**. You email yourself to talk to it; it treats that slice of your outbox as its inbox and short-term memory, and it inserts emails into your inbox to store routines, reminders, and rules for itself.

The builders pick email because it is an append-only, immutable record. The catch they name: users are reluctant to hand that data to a company.
