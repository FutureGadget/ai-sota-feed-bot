---
title: "Tracekit Box runs agents in micro-VMs where every network, credential, and write exit is signed"
date: 2026-10-31
theme: egress-and-escapes
evidence: [ccc859f642944e8a]
---
A new arXiv paper (research proposal; no independent evaluation seen) argues that the network, credentials, and write access agents need to install packages, call model APIs, and change deployable repos are the same paths they can use to leak data, steal a key, or alter an unapproved system.

Tracekit Box runs the agent in a micro-VM and routes each exit through a decision point that records a signed verdict. For platform teams, the useful idea is an auditable per-exit ledger rather than a single allow/deny at the sandbox edge.
