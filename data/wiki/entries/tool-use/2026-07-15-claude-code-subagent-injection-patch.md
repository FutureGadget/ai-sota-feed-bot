---
title: "Claude Code patches its Agent tool against injection carried in subagent-read content"
date: 2026-07-15
theme: guarding-the-call
evidence: [3f88ef2405b8fae7]
---
Claude Code 2.1.210 hardened its **Agent tool against indirect prompt injection** carried through content a subagent reads.

It is a shipped mitigation at the tool-call boundary, not only a policy argument for scoping what a tool may touch. See [prompt injection](/topic/prompt-injection) for the attack surface.
