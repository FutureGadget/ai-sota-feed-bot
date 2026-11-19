---
title: "LLM-written program judges match Sonnet 5.5 relevance labels for a one-time $0.17-0.49 per topic"
date: 2026-11-19
theme: cheaper-judges
evidence: [88caf412cf38ca9a]
also: [agent-evaluation]
---
ExecJudges has a frontier LLM turn assessment guidelines into an **executable program per topic** that uses only lexical matching, standard NLP libraries and pool statistics. Grading then costs nothing beyond running code.

On TREC DL 2019-2021 the programs agree with NIST assessors at the level of Claude Sonnet 5.5 judges. With a few human labels per topic, the ExecJudges-L variant beats per-topic classifiers on all seven collections and lands within about 0.05 Krippendorff's alpha of LLM judges given the same labels. Labels rank official runs at Kendall's tau 0.87-0.94. For builders: for repeatable grading, ask the model to write the judge once instead of calling it per item; the program is also inspectable and deterministic.
