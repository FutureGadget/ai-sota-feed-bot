---
title: "Repair shallow plan damage, replan deep damage, abandon when a fresh plan is not worth its cost"
date: 2026-11-17
theme: verify-and-replan
evidence: [56d285ed7661f5a6]
---
A theory paper derives when an agent should repair, replan, or give up after an action fails mid-plan. The optimal policy is a threshold on **effective disruption depth**, which depends on plan structure: one broken action forces about 1 + R(G)/n actions to be revalidated, where R(G) counts dependency-linked action pairs. A fully serial plan should switch to replanning at roughly **w times less** damage than a plan of w parallel chains.

Under repeated disruptions, the agent should keep patching a plan it would never choose fresh until accumulated **patch debt** outweighs repair's cost advantage. "Always replan" is optimal only when damage is predictably deep.

For builders: replace fixed retry or always-replan rules with a depth check over the plan's dependency graph.
