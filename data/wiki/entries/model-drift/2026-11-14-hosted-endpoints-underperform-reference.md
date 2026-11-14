---
title: "About 1 in 4 serverless endpoints for an open-weight model score below a reference deployment"
date: 2026-11-14
theme: serving-runtime-drift
evidence: [72eff2cf25179487]
also: [agent-benchmarks]
---
Artificial Analysis's Endpoint Accuracy Index v1.1 reruns more than 100 serverless endpoints of open-weight models on three equally weighted evals: BFCL v4 (tool calling), HLE (reasoning), and AA-LCR (long context). Each score is relative to a self-hosted reference at the recommended precision. Roughly one in four endpoints scored below its reference.

The index documents each reference down to hardware and serving stack, for example GLM-5.3 on eight B200s with SGLang and native FP8. It names the likely causes: quantization, custom kernels, changed inference settings, output-length limits, and bugs. Scores carry 95% confidence intervals because sampling variance alone can push an endpoint above 100%.

For builders: the same model name at two providers is two products. Rerun your own tool-calling evals when you switch providers.
