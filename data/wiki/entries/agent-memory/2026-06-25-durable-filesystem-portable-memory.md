---
title: "An S3-backed durable filesystem syncs agent memory files across laptop and cloud"
date: 2026-06-25
theme: shared-memory
evidence: [ce180fd0b3a2065e]
---
A developer built an **S3-based durable filesystem**, in Rust with Python and TypeScript SDKs and a CLI, that mounts anywhere so the memory Markdown files agents write on a laptop and in the cloud stay in sync.

It treats the memory store as a portable substrate that follows the agent between runtimes, the build-it-yourself answer to the cross-platform consistency managed services sell.
