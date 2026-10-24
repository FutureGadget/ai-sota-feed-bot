---
title: "TenseMem lets the model propose typed facts while a deterministic engine decides what is current"
date: 2026-10-24
theme: memory-integrity
evidence: [83ab5580b21e5403]
---
TenseMem is an embedded, open-source memory store in a single SQLite file with no server. The model proposes typed facts; the engine, not the model, resolves which one is current.

The target failure is similarity search returning both "I live in Delhi" and "I moved to Bangalore" and leaving the model to guess. Resolving supersession in code makes the current-state read deterministic. A rule-based extractor runs without an API key, and OpenAI, Anthropic, Ollama, LiteLLM, and Gemini plug in.

Early project README, no published benchmark. Treat it as a pattern: keep stale-fact resolution out of the prompt.
