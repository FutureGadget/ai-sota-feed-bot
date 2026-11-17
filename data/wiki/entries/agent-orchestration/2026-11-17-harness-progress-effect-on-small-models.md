---
title: "On small local models the harness decides whether a run writes anything; 85 empty runs still exited normally"
date: 2026-11-17
theme: harness-choice
evidence: [45715d71fbcd02a8]
also: [agent-benchmarks]
---
A ladder study crossed five shipped harnesses with 18 artifact-producing tasks and open-weight models from 0.75B to 4.7B, plus a 35.5B anchor. One completion-controlling harness, Mingbird, had the highest mean at every size.

Its edge came from progress, not from its completion checks. Disabling all six executable checks moved the mean by at most 0.117 with every interval including zero, while removing one repeat-blocking rule cost **0.411** at 0.75B. Of 357 usable runs, **127** left none of their declared artifacts, and **85** of those exited normally.

For builders: with small models, loop-breaking rules matter more than done-gates. Score runs by the artifacts on disk, never by exit status.
