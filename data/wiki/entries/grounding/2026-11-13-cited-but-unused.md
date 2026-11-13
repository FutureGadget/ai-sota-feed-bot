---
title: "Up to 15.7% of cited RAG claims come from model memory, and NLI citation checks cannot tell"
date: 2026-11-13
theme: proving-attribution
evidence: [9a823f949628f234]
---
The study swaps a fact in the retrieved passage for a false variant and re-queries. If the answer keeps the original fact, the claim came from parametric memory and the citation misstates its provenance.

- **Rate:** 1.2% to 15.7% of citable claims across five sizes of one model family and a second family, rising with model size.
- **Verification fails:** NLI checking, the standard approach, performed at chance, because a model answering from memory picks a citation that agrees with its output.
- **Best signal:** contrasting the model's output distribution with and without context, the strongest of ten attribution methods. The authors say it is still not accurate enough to act on.

A citation that entails the claim proves agreement, not use. Paper-reported.
