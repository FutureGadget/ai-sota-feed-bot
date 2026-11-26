---
title: "MeterRouter builds a per-query agent graph under a dollar budget, matching the best system at 82% less cost"
date: 2026-11-26
theme: routing
evidence: [851958f4eb1c5d85]
also: [multi-agent]
---
MeterRouter routes at the level of the whole collaboration: for each query it constructs which agents and models work together, under an explicit monetary budget. Across five benchmarks the authors report accuracy comparable to the strongest fixed multi-agent system at **82% lower cost**.

For builders: a fixed multi-agent topology pays its full price on easy queries. Budget-aware routing over the topology, not just the model, is where the savings in this paper come from. The numbers are author-reported on benchmarks; measure on your own traffic mix.
