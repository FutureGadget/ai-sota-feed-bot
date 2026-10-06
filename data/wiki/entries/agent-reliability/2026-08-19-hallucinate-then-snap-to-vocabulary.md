---
title: "Let the model hallucinate a label, then snap it to the real vocabulary with embeddings"
date: 2026-08-19
theme: hallucination-containment
evidence: [8961949ff68916c0]
---
Simon Willison describes Doug Turnbull's trick for tagging against a vocabulary too large for one prompt (his blog has **1,856 tags**). Ask the model to output tags with no knowledge of the existing vocabulary, then use **vector-embedding similarity** to map each guess to the nearest real tag.

It swaps a task the model is bad at (choosing from thousands of options) for one it does well (free generation plus retrieval). It only works because the embedding step grounds the hallucination instead of returning it as-is.
