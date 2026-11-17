---
title: "Text-similarity guardrails miss relayed injections and flag every legitimate quotation"
date: 2026-11-17
theme: model-defenses
evidence: [576e1bdcfd029627]
also: [multi-agent]
---
An injected instruction can keep working on downstream agents after its wording changes, while honest quotation produces high textual overlap. In a three-agent email relay, DonkeyRail, a public classifier built on BLEU, ROUGE-L and METEOR features, missed **8 of 19** outputs that still carried the injected procedure and flagged **70 of 192** legitimate replies, including every quotation and template reuse.

Recalibrating for few false positives did not transfer: on new templates it caught **1** functional output and raised 15 false alerts. The authors also found an operating-point error in all 21 published configurations of the classifier.

For builders: judge an inter-agent guardrail by whether the downstream behavior changed and what policy authorizes, not by surface overlap with the source text.
