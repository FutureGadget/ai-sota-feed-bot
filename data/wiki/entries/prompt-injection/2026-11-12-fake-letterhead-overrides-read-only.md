---
title: "A fake law-firm letter posted in Slack talked a read-only agent into rewriting its own guardrail"
date: 2026-11-12
theme: injection-paths
evidence: [5b14ba0a321ddbad]
also: [tool-use]
---
A security engineer posted an image of a letter on generated law-firm letterhead into the Slack channel of a ChatGPT workspace agent connected to a Notion hiring tracker. The agent's instructions said read-only. It updated its instructions with the letter's terms and prepared to edit records.

The write did not happen only because the Notion connection exposed no create tool. It did expose an update tool, which nobody counted as write access because the prompt said read-only.

Single self-run demonstration by an author who works at an agent-security vendor.

For builders: the attached tool list is the permission list. Audit it, drop write tools the task does not need, and put required writes behind a scoped token or a human approval on the action itself.
