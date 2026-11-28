---
title: "An agent-backed Dependabot bumps deterministically and calls the agent only when pins drift"
date: 2026-11-28
theme: upgrade-tooling
evidence: [53ff11b3ee1ec5a3]
---
Cole MacKenzie built Felix on Cloudflare after Dependabot bumped a Rust Docker image but left `rust-toolchain.toml` behind. Felix bumps versions deterministically first. An agent steps in only when the result is broken or out of sync: it reads the release notes and moves every related pin together.

Lockfile-only conflicts skip the agent and are just regenerated. Each repo gets one Durable Object holding its scan schedule. The agent runs in a container sandbox, and PR comments like `/felix hold react at 19` are honored or refused with a reason.

For builders: use deterministic tooling for the bump and the agent for the coupled edits it misses. That keeps model cost tied to the PRs that need judgment.
