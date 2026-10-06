---
title: "Field order in serialized records silently controls embedding retrieval quality"
date: 2026-06-30
theme: recall-quality
evidence: [648e4fc20120543d]
---
Embedding a structured metadata record means serializing its fields into a string, which forces a field order. A standard fine-tuned encoder **loses 7.4 nDCG@10 points** when the index is rebuilt under a different field order, because it learns absolute position instead of field labels. The paper proposes permutation-invariant fine-tuning to remove that dependence.

If you embed catalog or schema records, serialization is part of the retrieval model. Fix it before tuning the index.
