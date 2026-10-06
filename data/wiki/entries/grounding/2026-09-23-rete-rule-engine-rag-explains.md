---
title: "ai-rete-rag: a Rete rule engine makes the decision, RAG only explains it"
date: 2026-09-23
theme: proving-attribution
evidence: [010b63f98f068ab0]
---
For decisions that must be auditable (lending, fraud, clinical triage), ai-rete-rag runs two systems in series. A **pure-Python Rete engine evaluates YAML rules**: same facts, same verdict, every time. Then RAG retrieves passages from the organization's policy documents and an LLM writes a plain-English explanation citing them, **with no ability to change the verdict**.

The explanation cannot drift from what actually decided, the way a model's post-hoc rationale can. See [agent reliability](/topic/agent-reliability).
