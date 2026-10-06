---
title: "Routing in the harness cut Open SWE's median cost per task 64% with no quality drop"
date: 2026-10-02
theme: routing
evidence: [378de5b0a4ef1ffb]
---
LangChain's Open SWE classifies each thread's first human message into one of three tiers (GLM-5.3-Flash, GPT-5.6 Sol, GPT-6 Astra) and holds that model for the thread. Median cost per thread fell **64% versus always-frontier**, with no measurable quality change.

The reusable part is the build order: label a week of traces by task type, pick tiers off the cost-per-task Pareto frontier, write tier criteria from your own task mix, then A/B test on merged-PR rate and thumbs feedback. The router lives in the harness because tier criteria depend on the agent's own tasks. **Mid-thread re-routing is unsolved.**
