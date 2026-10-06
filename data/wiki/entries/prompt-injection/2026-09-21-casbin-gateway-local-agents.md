---
title: "Casbin Gateway puts the coding agents on a developer's machine behind one permission layer"
date: 2026-09-21
theme: harness-controls
evidence: [e73433c3ca4b5235]
---
Casbin Gateway is a local security layer for the coding agents on a developer's machine (Claude, Cursor, Codex). About **forty Casbin-policy permission switches per agent** gate tools, models, and providers; an unauthorized request returns a permission error instead of executing. It tracks usage from proxied requests and agent transcript files, and probes upstream API vendors to check they serve the model and protocol version they claim, grading each A-F. It binds to localhost by default and supports networked deployment with authentication.

It is the on-device counterpart to platform gateways such as Cloudflare's WriteGuard. The provider check partly answers the untrusted-router problem.
