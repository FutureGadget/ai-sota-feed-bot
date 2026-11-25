---
title: "Temperature-scaling the draft model lengthens speculative acceptance by up to ~10% at near-zero cost"
date: 2026-11-25
theme: draft-methods
evidence: [420b2dee4fa3c677]
---
Speculative decoding loses speed when the draft's distribution diverges from the target's. This paper applies post-hoc calibration, mainly standard **temperature scaling**, to the draft model, and reports acceptance-length gains of up to about **10%** across tasks with almost no added compute and no retraining of either model.

For builders: before swapping or retraining a drafter, try calibrating it against the target on your own traffic. It is a one-parameter fit.
