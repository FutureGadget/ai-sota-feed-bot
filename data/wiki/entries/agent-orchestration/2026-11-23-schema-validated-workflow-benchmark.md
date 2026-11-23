---
title: "Six Python stacks on one structured workflow: schema-valid output did not mean task-correct output"
date: 2026-11-23
theme: harness-choice
evidence: [81a62c33127d0095]
also: [agent-evaluation]
---
A benchmark protocol ran the same business workflows (extraction, compliance QA, and others) through PydanticAI, LangGraph, DSPy, CrewAI, Agno, and a plain SDK. Overall schema validity was 0.684 and mean automated quality 0.638. PydanticAI, LangGraph, and DSPy held near-ceiling validity and **0.91-0.94** quality; the SDK, Agno, and CrewAI scored substantially lower, with a workflow collapse for CrewAI.

Schema-valid outputs still drew many task-quality flags. The authors treat results as configuration findings, not proof about library features. For builders: score parseability and correctness separately in your own evals.
