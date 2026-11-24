---
title: "Changing only the Python hash seed flipped up to 17% of an agent's security-benchmark verdicts"
date: 2026-11-24
theme: adversarial-and-security
evidence: [846959515f07f1a4]
also: [agent-evaluation]
---
*TARE* shows that agent security verdicts depend on run details that carry no information about the system under test. On Agent Security Bench, runs with a fixed hash seed were identical across seven agents, but changing the seed changed up to **17%** of an agent's verdicts while attack success rate moved by at most **5 points**. The seed acts through tool ordering. TARE credits an effect to the agent, attack, or defense only when it exceeds this measured noise.

For builders: an ASR difference between two defenses may be tool order, not the defense. Rerun security evals across seeds and tool orders, and fix the ordering in any gate you rely on.
