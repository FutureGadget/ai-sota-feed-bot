---
title: "ReWEIGH calibrates visual evidence per token during decoding to cut VLM hallucination"
date: 2026-08-22
theme: hallucination-containment
evidence: [d5ceccd62fd0a295]
---
ReWEIGH calibrates **token-level ordinal visual evidence** during decoding in vision-language models. It projects visual-token states through the output head to measure how strongly the image supports each candidate token, instead of only judging the finished output.

It is the "contain it during generation, not just catch it after" approach, applied inside the decoding step.
