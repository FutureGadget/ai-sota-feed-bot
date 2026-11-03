---
title: "Tool poisoning succeeds in 22.9% of cells across 12 MCP frameworks; none defends"
date: 2026-11-03
theme: auth-and-governance
evidence: [f4762eccd1c3e217]
also: [prompt-injection]
---
The `mcpvenom` study ran 12 agent frameworks, 18 models and 45 poisoning scenarios (9,720 cells) with real tool execution. A canary HTTP receipt confirmed exfiltration. Overall attack success was 22.9%. Of the successes, 12.1% verifiably exfiltrated a secret. Model-level rates ranged from 0.4% to 49.7%.

Nine core frameworks clustered at 23-26%, so resistance comes from the model, not the framework. An audit found no intentional defense in any framework. A regex description scanner blocked 20 of 45 scenarios at a 7.2% false-positive rate, so metadata scanning is only a partial control. The authors report all five coordinated disclosures were rejected.
