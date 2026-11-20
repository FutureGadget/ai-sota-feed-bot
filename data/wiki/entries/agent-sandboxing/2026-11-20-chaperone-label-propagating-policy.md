---
title: "Project Chaperone tracks data labels through the model to enforce rules like \"no personal data by email\""
date: 2026-11-20
theme: permission-policy
evidence: [0d99e59a3a9a4cd4]
also: [prompt-injection]
---
Project Chaperone is an open-source harness, with a paper, that enforces high-level data policies on tool-calling agents. Labels such as PERSONAL **stick to data as it flows through the LLM**, and the harness blocks a tool call that would carry labeled data somewhere a rule forbids, such as outbound email. It also runs an explicit risk analysis before acting.

For builders: per-tool permissions cannot say "this data may not leave"; information-flow labels can. The cost is label tracking across every model step, and how well labels survive model rewriting is the open question.
