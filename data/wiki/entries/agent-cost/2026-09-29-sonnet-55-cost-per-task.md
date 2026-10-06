---
title: "Sonnet 5.5 keeps Sonnet 5's token price but cuts cost per task up to 30%"
date: 2026-09-29
theme: cheaper-models
evidence: [aae8bc1ed323e6eb, 09e1fe5d7a6f40d9]
---
Claude Sonnet 5.5 lists at **$2/$10 per million input/output tokens**, half of Opus 5.5's $4/$20, with the same $0.20 cache-read rate. Its per-token price matches Sonnet 5, but Anthropic reports it needs fewer tokens per task, so the same work costs **up to 30% less**. It is also on Amazon Bedrock.

Anthropic's routing rule: Sonnet for well-specified tasks with a way to check the result, Opus for long-horizon work. Default effort is `high` on the API but `medium` in Claude Code, so one model bills differently by surface; raising Sonnet to `xhigh` or `max` spends the saving.
