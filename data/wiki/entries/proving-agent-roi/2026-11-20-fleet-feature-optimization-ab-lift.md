---
title: "An agentic feature optimizer for production ranking models lifted a primary online metric 0.20% in A/B tests"
date: 2026-11-20
theme: outcome-evidence
evidence: [448f3844d5358398]
also: [agent-cost]
---
This system tunes feature selection across a fleet of production ranking models under shared pipeline-cost and per-model QPS limits. LLM agents propose cross features and run 10-25 asynchronous tuning trials; **deterministic tools execute and verify every experiment**, and a trimming step holds pipeline cost to budget.

Across production models it improved normalized entropy by 0.31% on average within budget, cut pipeline cost by 2.3% with no regression beyond noise, and **lifted a primary online metric by 0.20% in A/B tests** after launch. For builders: a rare agent ROI claim tied to an online A/B outcome, made possible by giving the agent hypotheses to propose and tools that measure them.
