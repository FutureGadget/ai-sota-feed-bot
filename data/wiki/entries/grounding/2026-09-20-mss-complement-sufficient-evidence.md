---
title: "For coding agents, recover a sufficient evidence set, not the top-ranked passages: 73.0% vs 61.4%"
date: 2026-09-20
theme: better-retrievers
evidence: [7fc462ef107af5f9]
---
A coding agent mid-task has already read much of what a retriever ranks highest, and a ranker can fill its budget with variants of one fact. **MSS-Complement** conditions on the agent's captured state and uses three semantic calls to propose a jointly sufficient set, find what is missing, and return 4-8 source units within budget.

On SERBench (500 held-out states from 45 repositories) it recovers a complete evidence set **73.0% of the time at five items, versus 61.4%** for embedding-based reranking.
