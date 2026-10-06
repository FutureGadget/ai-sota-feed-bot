---
title: "OpenWiki stores evidence-backed claims so codebase memory can correct itself"
date: 2026-08-26
theme: recall-and-curation
evidence: [34691d4d3bab21f8]
---
LangChain's **self-correcting memory** for OpenWiki stores evidence-backed claims instead of raw facts. It uses that evidence to detect when a claim has gone stale as the codebase changes, then corrects or drops it rather than retrieving whatever was written last.

It is a write-time defense against staleness and hallucination, pointed at codebase memory where the ground truth keeps moving.
