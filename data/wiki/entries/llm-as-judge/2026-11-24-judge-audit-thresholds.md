---
title: "judge-audit replays labeled human decisions to find the share an AI judge can take over at a target error rate"
date: 2026-11-24
theme: correcting-judge-error
evidence: [2b68eb06f1d125c1]
---
*judge-audit* is an open-source CI tool that replays decisions your reviewers already made and reports which share an AI judge can handle alone at an accepted error rate, with the confidence threshold to deploy, a held-out check, and an approximate bound. Its v0.6 study ran **12 judges** on **2,974 MASSIVE items** in three languages, pre-registered. Thresholds validated in English could not be shown safe in Spanish or Catalan: upper bounds on target-language error reached **8.65%** against a 5% target, above it in 5 of 6 tests. Declared confidence also missed accuracy by up to about 8 points.

For builders: re-validate a judge threshold per language and traffic slice before letting it act unreviewed.
