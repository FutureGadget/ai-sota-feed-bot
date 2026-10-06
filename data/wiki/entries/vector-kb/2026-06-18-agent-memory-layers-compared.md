---
title: "Letta, Mem0, Graphiti, and Cognee take different stances on graph vs. vector memory"
date: 2026-06-18
theme: hybrid-and-graph
evidence: [5c5003b8c444211d]
---
A survey of open agent-memory systems compares **Letta, Mem0, Graphiti, and Cognee**. Each packages external memory as a layer the agent calls, but they differ on whether facts live in a vector index, a knowledge graph of entities and relations, or both.

Choosing a memory layer is mostly choosing that stance. Graphs answer connected, multi-hop questions that flat embeddings miss, at the cost of modeling and upkeep.
