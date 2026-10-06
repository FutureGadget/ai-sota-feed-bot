---
title: "COBRA-Skills cuts skill-optimization cost 55-58% with bandit-guided evaluation"
date: 2026-09-13
theme: recall-and-curation
evidence: [db4dbac05b8debee]
---
**COBRA-Skills** frames skill improvement as budgeted sequential optimization over an evolving candidate pool. Contextual-bandit prioritization steers expensive execution-based evaluation toward the most promising or informative candidates instead of scoring every one.

Across six benchmarks and three target models it holds top-tier performance while **cutting optimization cost 55-58%** versus a SkillOpt baseline, with only 50 examples per benchmark. It makes the skill-evolution loop cheap enough to run routinely.
