---
title: "Under injected tool faults, agents recovered correctly 19-68% of the time and fabricated in 6-26% of runs"
date: 2026-11-24
theme: calling-reliability
evidence: [aab56d32e7581342]
also: [agent-reliability]
---
*When Tools Fail, Agents Fabricate* injected faults into **2,100 runs** across four tool-using agents. Correct recovery ranged from **19% to 68%**, and **6-26%** of runs ended with the agent confidently reporting a result the failed tool never produced. A verification-first monitor, which checks claims against actual tool outputs before accepting them, cut fabrication from **17.3% to 10.8%**.

For builders: a tool error is not a crash you will see; it is often a plausible answer. Return explicit error states from tools and check the final answer against the recorded tool outputs, not the agent's summary of them.
