---
title: "Deep Agents RubricMiddleware adds a grade-then-revise cycle with an iteration cap"
date: 2026-08-27
theme: verify-and-replan
evidence: [92884e6fce9aba7c]
---
LangChain's **RubricMiddleware** for Deep Agents turns a newline-delimited checklist of success criteria into a **grade-then-revise cycle**. A grader sub-agent with its own model, prompt, and optional tools checks the output, injects per-criterion feedback on failure, and the agent revises until it passes or hits a **max-iteration cap**.

Verification as a planning step ships as reusable middleware rather than a bespoke harness. The grader side is covered on [LLM-as-judge](/topic/llm-as-judge).
