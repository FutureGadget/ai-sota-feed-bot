---
title: "Simulated control evaluations test agent monitors with an LLM that fakes tool outputs"
date: 2026-10-26
theme: trusting-the-judge
evidence: [317b87334e0d2a63]
also: [agent-evaluation]
---
Redwood Research's paper on simulated control evaluations (SCEs) tests whether a monitor, the model that flags or blocks an agent's risky actions, would catch an agent deliberately trying to cause harm, such as quietly inserting a security flaw. An LLM simulates the tool outputs, so tests run under conditions closer to real deployment than static transcripts allow.

For builders: a monitor's catch rate on canned attacks overstates its real one. Measure it against an adaptive adversary in a simulated environment before trusting it as a gate.
