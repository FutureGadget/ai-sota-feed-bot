---
title: "Stripe runs a ReAct compliance agent on a dedicated service with guardrails and human oversight"
date: 2026-06-30
theme: loop-as-infrastructure
evidence: [1e062311eafafa88]
---
An AWS write-up of Stripe's financial-compliance agent describes a **ReAct framework** (reason, act, observe, repeat) running on a **dedicated agent service**, with guardrails, human oversight for accountability, and lessons on task decomposition.

The ReAct loop alone does not keep multi-step runs on track at production scale. Planning reliability is an architecture problem, solved with infrastructure around the loop, not a prompt problem.
