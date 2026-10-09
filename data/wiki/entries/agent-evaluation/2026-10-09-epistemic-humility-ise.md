---
title: "High task accuracy does not imply an agent admits unresolved uncertainty"
date: 2026-10-09
theme: domain-benchmarks
evidence: [4353ed3c68ccb423]
---
A new paper scores agents on **epistemic humility**: whether they identify, solve, and escalate knowledge conflicts, where retrieved evidence contradicts the model's prior or two sources disagree. Across four agents, higher accuracy did not track more humility. Some high-accuracy configurations noticed conflicts mid-run yet gave incorrect final answers without flagging uncertainty, and agents often detected conflicts early but lost them in later steps. Model-level interventions improved humility, often at the cost of accuracy.

For builders: grade trajectories for conflict handling, and check the final answer surfaces what the run noticed.
