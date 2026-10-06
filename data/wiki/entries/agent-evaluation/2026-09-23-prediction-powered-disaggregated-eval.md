---
title: "Prediction-Powered Smoothing estimates per-domain eval scores from small labeled samples"
date: 2026-09-23
theme: score-validity
evidence: [989be6ca1bd187d7]
---
**Prediction-Powered Smoothing** treats an evaluation set as a finite population and produces point and interval estimates for each domain mean — per task type or per conversation type in a deployed agent — when exhaustive labeling is too expensive.

Aggregate scores hide weak slices. This gives statistically grounded sub-scores, with intervals, instead of either a single number or noisy per-slice averages.
