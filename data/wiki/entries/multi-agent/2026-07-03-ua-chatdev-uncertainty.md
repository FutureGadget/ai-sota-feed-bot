---
title: "UA-ChatDev has role agents act on their own uncertainty to stop error propagation"
date: 2026-07-03
theme: when-it-pays
evidence: [8875da5519a24b6e]
---
UA-ChatDev targets **hallucination propagation** in role-based software-development agents. Existing frameworks treat every intermediate output as equally reliable, so a mistake made during requirements or design flows to every downstream role. UA-ChatDev's agents track their own confidence, and a low-confidence step triggers deliberation or a handoff instead of being passed on as fact.

Coordination reliability depends on agents knowing what they don't know, not only on topology.
