---
title: "Grith scores an agent's syscalls with 18 deterministic filters, no LLM in enforcement"
date: 2026-08-28
theme: local-sandboxes
evidence: [a2c038fcf0da7a87]
---
**Grith** is a security proxy for coding agents that intercepts security-relevant syscalls via **ptrace/seccomp-BPF** and scores each against **18 deterministic filters** (secret scanning, egress policy, destructive-op detection, taint tracking) into ALLOW, QUEUE, or DENY.

It targets the failure where, once auto-approve is on, the agent effectively approves its own actions. Keeping the LLM out of enforcement means injection cannot argue its way past the check.
