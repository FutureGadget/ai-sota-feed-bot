---
title: "Moving four of five routine agent jobs to open models cut a month's bill from $258.53 to $11.04"
date: 2026-11-20
theme: cheaper-models
evidence: [7a5e69e8b0d78e01]
also: [proving-agent-roi]
---
A practitioner ran five routine agent jobs for a month on Claude Sonnet 5.5 and on two open models. The Sonnet bill was **$258.53**; the cheapest setup that got every answer right cost **$11.04**. Four jobs moved with no wrong answers. The fifth failed on open models and stayed on the closed model.

The writeup traces most of the bill to the agent re-reading a roughly 14,000-token instruction file on every call, so Sonnet billed about 20,000 input tokens per call. For builders: price routine jobs per job against your own answer key, move the ones that pass, and cut the standing prompt before anything else.
