---
title: "Durable agents need current authority and retained ledgers before retrying an uncertain action"
date: 2026-10-29
theme: execution-and-identity
evidence: [7e505f680072dedd]
also: [agent-sandboxing]
---
A paper-reported conformance study ran 336 histories on native LangGraph and Temporal hosts, scoring recovery against a provider effect ledger hidden from the application. Checkpoint state, permission to dispatch, evidence of an external effect, and permission to reconcile are treated as separate obligations.

All 168 paired host cells matched. Retained-ledger reconciliation passed all 42 histories per host, including six with unknown outcomes held with reservations. Cached retry, revalidation before retry, and stable-key retry passed 30, 36, and 31 histories respectively. Resuming from a checkpoint is not enough: revalidate authority and reconcile against recorded effects first.
