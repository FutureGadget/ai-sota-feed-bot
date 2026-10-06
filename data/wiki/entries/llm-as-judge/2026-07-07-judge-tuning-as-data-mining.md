---
title: "LangChain: improving agents is a data-mining problem"
date: 2026-07-07
theme: cheaper-judges
evidence: [4a0a79e7203bae64]
---
LangChain describes its loop as **data mining, not labeling**: cluster failures out of real agent traces first, fine-tune a cheap judge on those clusters, then use the judge to hill-climb the agent.

What gets judged comes from observed failures, not a rubric drafted before any traces existed.
