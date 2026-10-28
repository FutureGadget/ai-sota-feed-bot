---
title: Novelty judges swing by 50+ points on small prompt changes
date: 2026-10-28
theme: trusting-the-judge
evidence: [1d6c5c59e46e52b9]
---
Ai2's "Old Ideas, Novel Problems" benchmarks LLM novelty judges on 154 high-novelty ideas drawn from ICLR 2026 peer reviews. Across six judges (GPT-5.1/5.2/5.4, Claude Sonnet 4.5, Opus 4.5/4.6), changing a few words in the prompt shifted pairwise accuracy by more than **50 percentage points** (paper-reported).

Retrieval and extra reasoning did not help consistently, and two purpose-built novelty systems scored below a plain prompted Opus 4.6 baseline. For builders: a judge validated on human-written papers may not transfer to generated ideas, so re-check any judge after every prompt or setup change.
