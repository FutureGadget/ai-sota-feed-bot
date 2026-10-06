---
title: "Lazy Grounding: true evidence for a nearby question cuts search-agent accuracy up to 17.3 points"
date: 2026-09-05
theme: adversarial-evidence
evidence: [a7ea832bc7e9c508]
---
Lazy Grounding shows a search agent can be misled without any false document. Using answer-changing rewrites of benchmark questions, each injected document **truthfully supports a nearby question** but surfaces for the original one, and agents adopt the nearby answer.

Accuracy drops **5.9 points on average and up to 17.3 points** across 12 model-benchmark combinations. Fact-checking retrieved text will not catch it; the check has to be whether the evidence answers *this* question.
