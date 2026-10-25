---
title: "Models can repeat a stated instruction in long dialogue yet stop obeying it"
date: 2026-10-25
theme: memory-integrity
evidence: [4179502a4cb9cc04]
---
A paper names a recall-compliance dissociation in long-horizon dialogue: the model can still repeat an instruction while failing to keep obeying it. The authors call this **State Integrity Collapse**, where a model preserves a stated constraint in recall but not in behavior.

This is paper-reported from the abstract excerpt.

For builders: a memory check that asks "does the agent still know the rule?" can pass while the agent violates it. Evaluate long sessions on compliance with constraints, not recall of them, and re-inject or enforce critical rules outside the model's conversational state.
