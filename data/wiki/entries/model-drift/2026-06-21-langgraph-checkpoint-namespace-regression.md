---
title: "LangGraph 1.2.6 fixes a checkpoint regression introduced two releases earlier"
date: 2026-06-21
theme: regressions-and-reverts
evidence: [1f04aad16ad88e88]
---
LangGraph 1.2.6 fixed **nested subgraphs inheriting the parent `checkpoint_ns`**, a regression introduced in 1.2.3. It also cancels running subgraphs on v3 stream abort.

Anyone who upgraded into the 1.2.3-1.2.5 window got broken checkpointing without touching their own code. Framework patch releases need the same regression gate as model upgrades.
