---
title: "LLM selection systems stay reliable with constrained schemas and a discriminator check"
date: 2026-08-24
theme: deterministic-boundaries
evidence: [d425cfc85457f214]
---
In an InfoQ talk on LLM-powered selection systems, Jendrik Jördening restricts model output to a **constrained schema**, separates semantic extraction (where the model is needed) from the deterministic code that acts on it, and validates the model's choices with a **discriminator model** before they reach the database.

He structures the pipeline as an MVC-style split so non-determinism stays in one layer instead of leaking into storage and downstream logic.
