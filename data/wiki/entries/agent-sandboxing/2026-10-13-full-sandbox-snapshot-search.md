---
title: "Restoring full sandbox snapshots beats restarting coding agents when state lives outside the repo"
date: 2026-10-13
theme: managed-platforms
evidence: [d1fefa038faa8d84]
---
A paper applies Go-Explore-style search to full **Daytona** snapshots: after a failed attempt, the agent restores an intermediate machine state and branches from it instead of restarting from scratch. Higher and cheaper solve rates depended mainly on progress outside the repository, such as databases and running services.

For builders: snapshot-and-branch pays off for long-horizon work spanning several services whose state a single diff cannot rebuild. For repo-only edits, a plain retry is enough. Sandbox platforms that expose snapshot and restore are the prerequisite.
