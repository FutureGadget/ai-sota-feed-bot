---
title: "Agents drift from what was evaluated; a behavioral identity ties eval to deployment"
date: 2026-09-13
theme: gaming-and-containment
evidence: [488d1511cc2dd895]
---
Production agents drift from the evaluated version through routine changes — prompt edits, tool-schema updates, policy shifts, knowledge-base refreshes, model fallbacks, memory effects — so a good eval is not authorization to deploy.

The proposal: track the agent by an identifiable **behavioral revision**, not a label like `customer-support-v4`, and chain seven stages under that identity: declare, evaluate, certify, authorize, execute, observe, audit. The question it answers is whether the certified agent is provably the one now running.
