---
title: "vLLM's AFD plugin disaggregates attention and FFN for MoE serving"
date: 2026-07-24
theme: engine-architecture
evidence: [94813f8b6bc86093]
---
The vLLM AFD plugin runs **attention and FFN computation on separate execution paths** for MoE serving, with GPU and Ascend NPU backends, connector-based execution, and graph and micro-batching ("ubatching") support.

Prefill/decode disaggregation splits a request by *phase*; AFD splits a single forward pass by *compute type*. That is a second knob for allocating hardware across the two halves of large open MoE models.
