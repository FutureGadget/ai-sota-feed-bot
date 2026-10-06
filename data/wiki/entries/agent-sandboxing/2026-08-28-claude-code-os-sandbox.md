---
title: "Claude Code's OS-level sandbox cuts permission prompts by 84% in Anthropic's testing"
date: 2026-08-28
theme: local-sandboxes
evidence: [c765441e9673d957]
---
Claude Code's sandbox confines filesystem access to the working directory and routes network traffic through a proxy enforcing a **domain allowlist**. Linux **bubblewrap** and macOS **Seatbelt** enforce both at the OS level. Anthropic reports it safely cuts permission prompts by **84%** in internal testing, and the implementation is open source.

It is a measured answer to approval fatigue: enforce the boundary in the OS so the human only sees prompts that matter.
