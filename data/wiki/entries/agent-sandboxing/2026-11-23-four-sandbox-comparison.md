---
title: "Hands-on review of nono, Docker Sandboxes, Microsandbox, and OpenShell: all 4-4.5/5, none at v1.0"
date: 2026-11-23
theme: local-sandboxes
evidence: [96ee621aa0ebe1e9]
---
Kudelski Security compared four coding-agent sandboxes on isolation, network filtering, and credential handling:

- **nono**: Landlock/seccomp or Seatbelt on a shared kernel; strongest credential injection, weakest isolation.
- **Docker Sandboxes**: a microVM per agent with live approval of blocked requests; closed source, filesystem policy is paid.
- **Microsandbox**: libkrun microVMs with metadata endpoints blocked by default; no HTTP path filtering or block log.
- **OpenShell** (NVIDIA): pluggable backends, per-binary policy, versioned rules and OCSF audit logs; early and needs a gateway.

None filters DNS exfiltration fully, and none can hide one file inside an allowed directory. For builders: keep secrets outside the project tree, and pick the sandbox your team will leave enabled.
