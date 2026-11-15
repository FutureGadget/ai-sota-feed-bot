---
title: "Scoping agents by job instead of by account made human feedback reviewable and transferable"
date: 2026-11-15
theme: shared-context
evidence: [65922cfb61a324a6]
---
Actively AI first ran **one agent per sales account**. Reviews were scattered, reps context-switched between agents, and a lesson learned on one account (how to outbound, how aggressive to be) had no clean way to reach the others.

Its rebuild on Deep Agents scopes each agent to a **"motion"**, one job such as outbounding. A rep reviews a batch of similar tasks together, and feedback on one transfers to all of them. LangChain's takeaway: scope an agent so feedback is easy to give, and invest in the review UX, because learning from experts is the bottleneck for subjective, long-horizon goals (vendor case study).

For builders: draw agent boundaries around the knowledge that must be shared, not around the data object being worked.
