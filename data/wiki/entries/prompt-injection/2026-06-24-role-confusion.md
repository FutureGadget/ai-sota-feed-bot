---
title: "Prompt injection is role confusion: models can't separate operator instructions from data"
date: 2026-06-24
theme: injection-paths
evidence: [f26c96cfcb192832]
---
Charles Ye, Jasmine Cui, and Dylan Hadfield-Menell frame prompt injection as **role confusion**. An LLM has no reliable channel that separates "instructions from my operator" from "data I was asked to process," so text arriving as a tool result or fetched page can take the operator's role and be obeyed.

That explains why prompt hygiene can't fix it: the model is doing what it was built to do. Durable controls live in authorization, limiting what an obeyed instruction can reach, not in detecting "malicious" strings.
