---
title: "Silent grader and logging bugs reorder public agent leaderboards"
date: 2026-11-06
theme: trusting-the-score
evidence: [7dfaaa125cb6bf17]
also: [agent-evaluation]
---
A paper (paper-reported) audits the HAL and tau2-bench leaderboards from published artifacts alone. A general agent trailed an airline-benchmark scaffold by 13 points because it often ended conversations in a way that never triggered grading: only about half its episodes were scored, the rest stored as failures. Grading the other half closed the gap without rerunning anything.

Three more errors surfaced: nested model calls counted twice in a cost column, grader-written actions logged as agent actions, and a mode check misreading four files that cut scores by 59-82 points with no error. HAL maintainers confirmed three.

Report the graded fraction, aggregate cost from root spans, tag action provenance, and pin evaluator versions.
