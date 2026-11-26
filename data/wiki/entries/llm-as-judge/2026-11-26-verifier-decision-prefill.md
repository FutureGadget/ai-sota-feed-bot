---
title: "A span verifier's verdict rests on one branch token; stopping there cuts serving cost 85% at the same F1"
date: 2026-11-26
theme: cheaper-judges
evidence: [fbde8cddf276738d]
---
A generative verifier often keeps decoding to quote and classify errors when the caller only needs "is any claim unsupported?". In a frozen 2B span verifier, the choice between an empty error list and its first object comes before any localization. *Prefill1* supplies the seven fixed syntax tokens as input and generates only that branch token. On **2,015** code-agent responses it cut eager resident serving by **84.84%** versus full generation, at F1 **83.43** versus **83.41**. Under compiled execution the extra saving over stopping at the branch was 6.7-26.7%.

For builders: if a verifier gates a pipeline, read its decision token and generate spans only for flagged items.
