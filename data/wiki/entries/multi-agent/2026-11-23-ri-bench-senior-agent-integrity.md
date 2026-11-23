---
title: "RI-Bench: senior agents often defer to generic subordinate reviews and drop stated limitations"
date: 2026-11-23
theme: oversight-and-safety
evidence: [459d70ee53e01cfa]
---
RI-Bench tests whether a "senior" LLM agent uses subordinate material faithfully in hierarchies modeled on peer review, appellate courts, and parliamentary committees. The paper reports that senior agents frequently defer to generic reviews instead of weighing their content, and drop limitations that a subordinate (such as a witness) stated explicitly.

For builders: in supervisor-worker designs, the supervisor is a lossy aggregator. If a worker's caveat must survive, carry it as a structured field the supervisor cannot summarize away, and test for its presence in the final output.
