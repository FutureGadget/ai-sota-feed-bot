---
title: "In 72% of failed long runs the trajectory already held evidence against the error, and no agent acted on it"
date: 2026-11-13
theme: verifying-the-work
evidence: [94045c979b35ebe7]
also: [multi-agent, agent-tracing]
---
A full read of 95 failed runs from six multi-agent systems (Who&When and MAD corpora) traced each fault from origin to consequence instead of labeling the symptom.

- **Faults enter early:** median at 18% of the run, mostly wrong decisions or fabrications about task state.
- **Evidence goes unused:** 72% of runs contained contradicting evidence before the failure; in 88% of those no agent acted on it.
- **Flags do not repair:** something flagged a deviation in 31% of runs, and no response removed the bad state.

The controls that reach most episodes are an independent judge reading the unused evidence, a task contract fixed at admission, and re-checking beliefs against the environment. Restoring the agent's own state would have sufficed in 35 of 95 runs. Paper-reported, hand-annotated.
