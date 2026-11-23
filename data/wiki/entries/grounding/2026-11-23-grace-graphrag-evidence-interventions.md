---
title: "GRACE perturbs GraphRAG evidence in four controlled ways to show where answers ignore or misuse it"
date: 2026-11-23
theme: adversarial-evidence
evidence: [4a7318bd3c25667f]
also: [vector-kb]
---
GRACE is a 4,028-question GraphRAG benchmark built from LC-QuAD 2.0 queries over Wikidata. Each question is replayed under four controlled evidence interventions, so a wrong answer can be traced to how the model integrated the retrieved graph rather than to retrieval alone. The authors' QCFSE-SA method raises controlled-state accuracy from **57.17%** to **62.78%**.

For builders: end-to-end RAG accuracy mixes retrieval and integration failures. Perturbing evidence while holding the question fixed separates them.
