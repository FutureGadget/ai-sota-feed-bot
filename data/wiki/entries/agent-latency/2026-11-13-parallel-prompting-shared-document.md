---
title: "Decoding many questions over one cached document as parallel streams runs 3.7-6x faster"
date: 2026-11-13
theme: kv-state
evidence: [6711271701a16ef8]
also: [llm-as-judge, agent-cost]
---
Prefix caching removes repeated prefill when many questions share a long document, but each decode step still reads the document's KV cache once per question, so decoding is bound by memory bandwidth.

Parallel Prompting decodes P questions as P streams of one request. Each step reads the shared document once, and a stream-id attention mask inside the kernel keeps every answer conditioned only on the document and its own question.

- **Implementation:** about 80 lines across three SGLang files plus a small engine package.
- **Result:** 3.7x faster than stock SGLang on an A100 and 5.9-6.0x on an RTX A6000, with CodeLlama-7B, 8k-16k-token documents, and 64-256 questions per document.

It fits LLM-judge, labeling, and document-QA batches. Paper-reported on one 7B model.
