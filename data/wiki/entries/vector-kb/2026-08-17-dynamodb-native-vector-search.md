---
title: "DynamoDB adds native vector search alongside application rows"
date: 2026-08-17
theme: datastores-you-run
evidence: [7b2b4d44ea281840]
also: [grounding]
---
Amazon DynamoDB now stores embeddings next to application data and runs approximate nearest-neighbor queries through a **`SearchVectors` API**, with filtered similarity search and configurable indexes. Reported specifics: up to 4,096 dimensions, Euclidean/cosine/dot-product distance, and single-digit-millisecond latency at a claimed trillions-of-vectors scale.

It removes the sync-two-systems overhead for teams already on DynamoDB. The trade is a new billing surface: cost is metered per byte for data written, data processed per search, and data stored, on top of standard DynamoDB charges.
