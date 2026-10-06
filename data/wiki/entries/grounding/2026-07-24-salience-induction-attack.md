---
title: "Salience Induction redirects multi-hop RAG agents with only true facts, at 83.3% success"
date: 2026-07-24
theme: adversarial-evidence
evidence: [20a176e41161c528]
---
Salience Induction is a third attack channel beyond content poisoning and prompt injection: **truth-preserving edits** to fact position, emphasis, framing, and semantic proximity redirect a multi-hop agent's reasoning with no false claims and no instructions.

- Across five model families (GPT, Claude, Gemini, DeepSeek, Qwen) and ReAct, Reflexion, and tool-calling agents, a 30% edit budget reaches **83.3% attack success**.
- The strongest baseline defense still lets 75.7% through.
- The authors' Salience Normalization cuts it to 15.3% (23.6% under adaptive attacks).

Content filters will not catch this; the defense has to normalize how evidence is presented.
