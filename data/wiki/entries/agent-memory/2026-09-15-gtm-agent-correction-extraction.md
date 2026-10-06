---
title: "LangChain's GTM agent learns per-rep style by diffing human edits against its drafts"
date: 2026-09-15
theme: recall-and-curation
evidence: [27f2f50d69e9ceef]
---
LangChain's **GTM Agent** diffs a sales rep's edited draft against the agent's original to extract structured per-rep style observations. It writes them to Postgres keyed by rep and loads that record before every future draft, with a **weekly cron job compacting** the store. LangChain reports a 250% lift in lead conversion and 40 hours saved per rep per month.

The write is triggered by a human correcting the agent's output, a third write discipline beside automatic capture and explicit saves.
