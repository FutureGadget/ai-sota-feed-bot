---
title: "HUB-J mines human-vs-judge disagreements to find and regress out judge bias factors"
date: 2026-11-26
theme: correcting-judge-error
evidence: [6cacf0d6b431e506]
---
HUB-J is a training-free method for auditing an LLM judge. It starts from cases where human and judge verdicts disagree, uses them to discover the factors that bias the judge, measures how strongly each factor sways verdicts, and then applies a regression correction to reduce bias-driven verdict flips.

For builders: the human labels you already keep for judge calibration can also name *which* features skew the judge. That turns a single accuracy number into a list of biases to correct or test against.
