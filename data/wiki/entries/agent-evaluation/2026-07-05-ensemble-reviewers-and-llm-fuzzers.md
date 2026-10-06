---
title: "Ensembled reviewer personas cut false positives more than a stronger single model"
date: 2026-07-05
theme: grading-trajectories
evidence: [d8ea565801623af0]
---
Dan Luu's notes on agentic coding report two testing findings:

- **LLM-written fuzzers** find real, serious bugs within minutes but leave coverage gaps a quick hand-written fuzzer would catch, so bug-finding recall is not proof of thorough testing.
- **Ensembling reviewers** — independent agents checking the same artifact under different personas, including a deliberately contrarian one — cuts false positives more reliably than swapping in a stronger model.

The process around the model carries as much weight as the model choice.
