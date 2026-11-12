---
title: "Where a tool error lands in the conversation changes whether the model retries, fixes, or quits"
date: 2026-11-12
theme: calling-reliability
evidence: [41573f419013b0c4]
---
A paper holds the error text fixed and varies its placement, guidance, retained history, and turn structure across 13 open models from 3B to 70B parameters.

Delivering the error as a new user turn that keeps the failed exchange avoided a severe stopping failure seen in Llama models when that exchange was removed. As an opt-in recovery layer in an inference engine, it raised ToolMaze success on explicit errors by 14.2 points for 7-8B models and 10.5 points for 32-70B models.

It showed no measurable gain on 24 tasks with silent corruption and was not best for every model. A client told the exact fault kind did better still. Paper-reported.

For builders: test error delivery per model, and pass a typed fault kind where the harness has one.
