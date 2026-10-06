---
title: "Cloudflare Computer gives agents a persistent, stateful environment on isolates"
date: 2026-08-09
theme: managed-platforms
evidence: [2d67d91e54fb9eb8]
---
**Cloudflare Computer** is an open-source runtime that gives agents something closer to a durable "computer" than an ephemeral container, built on **Cloudflare isolates** for fast serverless execution.

Cloudflare now ships both ends of the spectrum: self-expiring temporary accounts and a persistent environment. Ephemeral versus durable becomes a per-workload choice, with durable state widening what a hijacked session can leave behind.
