---
title: "How much memory helps depends on the model: a weak model did better with 29 guidelines than with 199"
date: 2026-11-20
theme: recall-and-curation
evidence: [32373812989fabcd]
also: [agent-evaluation]
---
IBM mines one to three lessons per trajectory, consolidates them into guidelines, and ships the pipeline in the open-source `altk-evolve` library, CUGA, and watsonx Orchestrate. On AppWorld, DeepSeek-V3.2 kept improving with all 191 guidelines (**+9.5 points** task completion). gpt-oss-120b went from 39.9% to 51.2% with all 199 guidelines but to **55.4% with a selected subset of about 29**.

The failure list is the useful part: a high-support guideline that backfired, provenance silently dropped during consolidation, a swallowed API error that failed every task while logging plausibly, and a baseline confound that nearly faked a win. For builders: tune memory volume per model, keep provenance through consolidation, and check that a memory gain is not a harness artifact.
