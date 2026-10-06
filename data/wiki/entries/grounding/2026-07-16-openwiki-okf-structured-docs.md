---
title: "OpenWiki 0.2 adopts OKF so agents can filter codebase docs by metadata instead of searching"
date: 2026-07-16
theme: retrieval-architecture
evidence: [ace88b2c5ecc23e1]
---
OpenWiki 0.2 generates codebase wikis in **OKF**, a proposed open format that adds YAML front matter (tags, categories, timestamps), changelogs, and directory index files to doc pages.

An agent can filter to "every doc tagged `billing`" directly instead of running an open-ended search. It is the structured-recall argument applied to the docs coding agents ground their answers on.
