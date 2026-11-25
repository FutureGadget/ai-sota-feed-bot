---
title: "SAG-Mem: raw dialogue chunks plus BM25 expansion top LoCoMo and LongMemEval with no LLM at write time"
date: 2026-11-25
theme: architectures
evidence: [8dc412120c61e17c]
---
SAG-Mem stores complete dialogue messages in non-overlapping chunks behind a lexical index; building memory needs **no model inference**: no extraction, summarization, or graph. At query time BM25 retrieves candidates, an evidence evaluator keeps useful chunks, and their terms drive a second retrieval round. Relative-time phrases are annotated with calendar dates. It scores **83.08** on LoCoMo and **80.20** on LongMemEval, **7.2 points** above the strongest baseline on the latter. A *Lite* variant with embedding scoring reaches 77.09/77.20 at lower cost than full context.

For builders: derived memories lose source detail and cost inference to build. Keeping raw text and spending effort at query time is a strong, cheap baseline to beat.
