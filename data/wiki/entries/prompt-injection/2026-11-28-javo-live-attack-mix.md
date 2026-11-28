---
title: "On public website agents, half of real attack prompts target the system prompt"
date: 2026-11-28
theme: injection-paths
evidence: [90a6fcc6c7d96bc4]
---
Javo, which runs agents on hundreds of business websites, grouped November 2026 attack prompts from its logs into seven types. Direct prompt injection and instruction extraction by trick were **24% each**, so 48% went after the agent's instructions. Model fingerprinting came next at 18%. Role play and fake authority ("operator debug mode, SRE ticket 9912") were 6% each.

The riskier types are not rare. **12%** were server-side request forgery, giving the cloud metadata address 169.254.x as "my website" for the agent to fetch. Another 12% hid injections in form fields such as the name field. These are vendor-reported figures from one sample.

For builders: assume a public agent's prompt will leak. Block link-local and internal addresses in its fetch tool.
