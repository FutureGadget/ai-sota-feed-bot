---
title: "Hidden instructions in a Word document can make Copilot spread the injection to other documents"
date: 2026-07-30
theme: injection-paths
evidence: [dc6dd2ecfc18702f]
---
Håkon Måløy upgraded prompt injection against Copilot for Word into a **self-replicating worm**. Hidden instructions in a document later used as source material are read as part of the user's request, and they tell Copilot to copy the same payload into the documents it produces. One poisoned file seeds future output with the attack instead of causing one compromise.

An agent that treats fetched content as instructions can become the vector for the next victim. Content provenance matters for what an agent writes, not only what it reads.
