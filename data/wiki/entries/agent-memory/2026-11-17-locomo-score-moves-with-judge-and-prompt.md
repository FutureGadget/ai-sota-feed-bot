---
title: "Swapping only the judge moves a LoCoMo memory score 7.2 points; the answer prompt moves it 9.3"
date: 2026-11-17
theme: measuring-memory
evidence: [fe2344cdcbd096cd]
also: [llm-as-judge]
---
A study of LoCoMo, the common long-term conversational memory benchmark, reran 1,540 questions under two answer models, two answer prompts and three LLM judges. Changing only the judge moved a score by up to **7.2 points**; changing only the answer prompt, by up to **9.3**.

The memory system under test, Becos, beat a whole-conversation baseline with gpt-4o-mini (79.7 vs 73.0) from a context with 90% fewer characters, but tied it with gpt-4.1-mini (83.2 vs 83.1). Its configuration was tuned on LoCoMo itself, so there is no held-out set.

For builders: a memory vendor's LoCoMo number is only comparable if it names the judge, answer prompt and baseline. Rerun the whole-context baseline under identical conditions before believing a gap.
