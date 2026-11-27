---
title: "CypherMAS isolates message routing in multi-agent graphs; models above 27B still degrade as the graph widens"
date: 2026-11-27
theme: long-horizon-and-subsystems
evidence: [2c2c060d34af1ace]
also: [multi-agent]
---
CypherMAS tests only communication. Agents in chain, star, bipartite, or ring graphs must route ciphered messages to the peer that holds the decoder. The optimal route is known, so the benchmark counts wasted LLM calls and pinpoints where a message got lost. Across eleven open-weight models from 4B to 753B, small models fail at routing and tool use, dense models above 27B degrade as graph diameter grows, and even successful runs use more calls than the minimum.

For builders: a multi-agent failure can be a delivery failure, not a reasoning failure. Count hops and redundant calls per topology before you add another agent to the graph.
