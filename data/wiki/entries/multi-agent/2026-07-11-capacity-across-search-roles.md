---
title: "In hierarchical search agents, which role gets the bigger model matters"
date: 2026-07-11
theme: when-it-pays
evidence: [a07007d77a70dc10]
---
"Think Big, Search Small" splits hierarchical search into a **delegation role** (task decomposition), an **execution role** (retrieval and evidence extraction), and an answer-generation role held fixed as a control. It then varies model capacity per role instead of running one model everywhere.

Capacity is not interchangeable between roles: the same topology can win or lose depending on which role gets the larger model. Size each role on purpose.
