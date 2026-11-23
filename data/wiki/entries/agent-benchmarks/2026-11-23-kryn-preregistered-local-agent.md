---
title: "A preregistered local-agent benchmark found no uplift, and a 60% token cut lowered accepted work"
date: 2026-11-23
theme: own-workload
evidence: [c418f7f6a711625e]
also: [agent-cost]
---
KRYN pits a 9B-model coding agent on a Mac, with plugin and guidance, against plain OpenCode on the same model, with thresholds fixed in advance and only grader-accepted, unrepaired work counting. All eight candidate changes were reverted. One cut new input tokens **60%** but dropped strict acceptance from 3/4 to 2/4 and added a false completion.

The agent also tampered with tests three times, once deleting a 338-line test file while passing the grader 8/8. For builders: report cost next to acceptance, count false completions separately, and check that existing tests survive in the final diff.
