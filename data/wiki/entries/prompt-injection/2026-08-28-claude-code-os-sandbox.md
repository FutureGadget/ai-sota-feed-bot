---
title: "Claude Code's OS-level sandbox cuts permission prompts by 84% in Anthropic's testing"
date: 2026-08-28
theme: harness-controls
evidence: [c765441e9673d957]
---
Claude Code's sandboxing confines filesystem access to the working directory and routes network traffic through a proxy that enforces a domain allowlist. Linux bubblewrap and macOS Seatbelt enforce both, so **the boundaries hold at the OS level, not in the model**. Anthropic reports it safely cuts permission prompts by **84%** in internal testing. The implementation is open source.

Fewer prompts counters approval fatigue, where reviewing dozens of prompts an hour trains users to rubber-stamp. The sandbox still doesn't scope the credentials inside it.
