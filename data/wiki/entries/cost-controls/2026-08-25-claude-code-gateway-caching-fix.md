---
title: "Claude Code fixes prompt caching that silently broke behind LLM gateways"
date: 2026-08-25
theme: caching-and-filtering
evidence: [09d0c8e5c7031ff7]
---
Claude Code v2.1.237 fixed **prompt caching for sessions using an LLM gateway or custom base URL**. Before the fix, caching could stop firing on those sessions without a visible signal.

A caching default is infrastructure with its own failure mode. Teams routing through a gateway should monitor cache-hit rate, not assume it once the feature is on.
