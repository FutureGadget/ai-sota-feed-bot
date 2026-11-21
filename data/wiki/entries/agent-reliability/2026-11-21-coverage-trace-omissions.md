---
title: "COVERAGE-TRACE detects omitted facts in summaries by perturbing the source, not the output"
date: 2026-11-21
theme: hallucination-containment
evidence: [cd04a0a732ffd2db]
---
Omissions leave no output span to check, so faithfulness checkers miss them. COVERAGE-TRACE swaps one source fact for type-matched alternatives, keeps the summary fixed, and measures how much the summary's likelihood changes. A summary that covers the fact should react more.

On 80 matched QMSum pairs across four open-weight models, it reaches **0.764-0.825 AUROC** against 0.640 for the best text-only baseline. Adjusting for meaning-preserving paraphrases drops it to **0.591-0.624**. For builders: it is a useful extra signal for "did the summary drop the decision", but not yet a wording-independent coverage score.
