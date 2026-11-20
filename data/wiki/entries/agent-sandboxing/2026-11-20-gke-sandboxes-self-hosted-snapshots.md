---
title: "Self-hosted GKE agent sandboxes with sleep-and-resume run at 1.9¢ per awake hour"
date: 2026-11-20
theme: managed-platforms
evidence: [8965cbc03281cfdd]
also: [agent-cost]
---
`gke-sandboxes` is an open-source Terraform setup that gives each cloud agent its own Linux sandbox in your own Google Cloud project. A sandbox runs commands and keeps files; it can sleep while the user is away and resume under the same ID with its filesystem snapshot intact. A sleeping sandbox costs only storage.

The author reports about **1.9¢ per awake hour** for 2 vCPU / 4 GB, cluster overhead included, against 16.6¢ list price at Daytona and E2B. That comparison is the author's own. For builders: at steady volume, a self-hosted sandbox fleet can undercut managed providers by close to 9x, if you take on running the cluster.
