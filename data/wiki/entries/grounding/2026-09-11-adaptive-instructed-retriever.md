---
title: "Databricks' Adaptive Instructed-Retriever learns per query how hard to search, at half the latency"
date: 2026-09-11
theme: better-retrievers
evidence: [9dba62cbb9d1736b]
---
Databricks' retriever takes enterprise schemas and custom instructions as input and uses **reinforcement learning (CISPO)** to decide when one parallel search pass is enough and when a question needs sequential multi-hop search, with search cost in the reward.

It matches Claude Sonnet 5 and GPT-5.6 Luna answer quality at about **5.8s end-to-end, roughly half the latency**, and the vendor reports it dominates their quality-vs-cost curves across the retrieval budget. Search effort becomes a learned per-query decision, not a fixed step count.
