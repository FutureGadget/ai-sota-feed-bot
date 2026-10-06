---
title: "A DeBERTa plus MC Dropout detector reaches F1 0.915 on HaluEval but transfers poorly across domains"
date: 2026-09-17
theme: hallucination-containment
evidence: [70ffdcd5e3598c72]
---
A response-level detector combines fine-tuned **DeBERTa-v3**, Monte Carlo Dropout uncertainty, and temperature-scaled calibration. On HaluEval it reaches **F1 0.915 and AUROC 0.977**, and MC Dropout inference lifts accuracy to 93.2%.

The caveat matters for production: general-domain training transfers poorly to the SciFact biomedical benchmark (**F1 0.52**), and domain-matched PubMedBERT only reaches F1 0.63. A cheap detector is precise enough to gate on in-domain, but each domain needs its own training.
