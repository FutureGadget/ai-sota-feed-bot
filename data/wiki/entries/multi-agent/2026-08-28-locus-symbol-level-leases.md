---
title: "Locus locks individual code symbols with TTL leases so agents can share a repo"
date: 2026-08-28
theme: parallel-coding-agents
evidence: [0b15399105eca482]
---
Locus is a Rust AST engine for multi-agent coding swarms that takes **symbol-level TTL leases**: it locks one fully qualified symbol (e.g. `src/auth.rs::login`) only while an agent needs it, with heartbeat renewal and automatic expiry. Acquisition is claimed at under 2µs.

Concurrent agents can share a repo without full branch-and-worktree separation, catching the actual write conflict instead of walling off whole files. Early-stage project; the latency figure is the author's.
