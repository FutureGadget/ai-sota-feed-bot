---
title: "Zero-temperature judges still flip verdicts; the most consistent one was right only 51% of the time"
date: 2026-10-11
theme: trusting-the-judge
evidence: [5a0ce18b71c2722a]
also: [agent-evaluation]
---
A reliability audit stress-tested six frontier models as judges across four benchmarks, five prompt formats, two presentation orders, three temperatures, and ten repetitions. Verdicts changed across identical runs at temperature zero, and swapping answer order flipped the majority of verdicts on hard tasks. The most deterministic judge was perfectly consistent only by repeating wrong verdicts, agreeing with ground truth **51%** of the time.

The authors propose a *trustworthy verdict rate*: the joint probability a verdict is reproducible, order-invariant, and accurate. Holistic rubric scoring beat pairwise win-rate and any single prompt tweak.

For builders: measure consistency and order-invariance per item, not just agreement, and prefer rubric scores over pairwise comparisons.
