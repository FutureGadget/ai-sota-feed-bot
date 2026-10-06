---
title: "Only 7% of agent turns needed a frontier model; routing cut cost 74%"
date: 2026-08-12
theme: routing
evidence: [26b283e0296ba33f]
also: [proving-agent-roi]
---
LangChain benchmarked NVIDIA's **NeMo Switchyard** router on 145 agent tasks. **Only 7% of turns needed a frontier model**; routing the rest to cheaper models cut total cost **74% for six points of accuracy**.

Most of an agent's turn-by-turn spend goes to calls that did not need frontier capability. Whether six points is an acceptable price depends on the task, which is why the routing policy needs an eval on your own workload.
