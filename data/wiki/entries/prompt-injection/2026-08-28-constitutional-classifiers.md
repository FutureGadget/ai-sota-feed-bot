---
title: "Constitutional Classifiers cut jailbreak success from 86% to 4.4% for 23.7% more compute"
date: 2026-08-28
theme: model-defenses
evidence: [bb6ac706c8cdd78f]
---
Anthropic's Constitutional Classifiers train input and output filters on synthetic data generated from a written "constitution" of allowed and disallowed content. In red-teaming, unguarded Claude was jailbroken in **86%** of attempts on the target categories; with the classifiers, **4.4%**. The cost was 23.7% more inference compute and no statistically significant rise in refusals of harmless queries across 5,000 conversations. A public demo (339 participants, 300,000+ messages) surfaced one confirmed universal jailbreak.

It is the strongest measured case for guardrail layers. It is still a screening layer an adversary can target, not a fix for role confusion.
