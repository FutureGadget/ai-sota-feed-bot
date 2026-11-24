---
title: "Adaptive injections bypass harness consistency checks and turn risk auditing into a new attack surface"
date: 2026-11-24
theme: injection-paths
evidence: [8f913d3c64972156]
also: [agent-sandboxing]
---
*Conartist* attacks two common computer-use harness defenses. It embeds malicious steps so they look causally required by the user's goal, which passes consistency checking. It then probes the risk auditor's feedback and adapts, either staying under the audit threshold or inducing extra high-risk actions through the audit itself. Across five backbone models it reports **32.12%** attack success on a 576-instance set.

For builders: a defense that the attacker can query is a defense the attacker can learn. Keep auditor feedback out of the agent's visible context, and red-team with adaptive attacks rather than a fixed prompt list.
