---
title: "Separating test-writer from coder: hidden holdout suites reject 20 of 35 coding-agent runs"
date: 2026-11-25
theme: verifying-the-work
evidence: [2f5762523e95d678]
also: [agent-evaluation]
---
A practitioner applied Kaggle's private leaderboard to coding agents. Separate sessions write public tests and hidden tests from the same spec; a third writes a reference implementation, and hidden tests it fails are discarded. The implementing agent works in a sandbox that cannot read the hidden suite, which decides acceptance. Across about **2,500** sandboxed runs, deliberate overfitting was rare; guessing at unstated behavior was the common failure. In one Opus setup, **20 of 35** runs failed the hidden suite.

For builders: "all tests pass" from the agent that wrote the tests is self-grading. A held-out suite from a separate session is cheap and catches what the agent assumed rather than built.
