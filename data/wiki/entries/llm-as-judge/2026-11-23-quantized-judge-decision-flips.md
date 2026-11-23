---
title: "4-bit quantization flipped 1-12% of judge preferences while benchmark accuracy barely moved"
date: 2026-11-23
theme: cheaper-judges
evidence: [db1ba5abb7620254]
also: [agent-evaluation]
---
*The Vulnerability Window* quantized reward models and LLM judges to 4 bits and found **1.1-12.3%** of RewardBench preference decisions flipped, even when aggregate accuracy stayed nearly unchanged. The flips matter most where the judge picks among many candidates: they changed best-of-64 selections far more often than final answers.

For builders: a quantized judge can match its full-precision score and still pick different winners. Before cutting judge cost this way, compare per-item decisions against the unquantized judge, not the headline accuracy.
