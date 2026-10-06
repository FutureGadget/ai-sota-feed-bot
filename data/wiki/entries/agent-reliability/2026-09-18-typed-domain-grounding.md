---
title: "Typed Domain Grounding lets a host language's type checker catch invalid LLM-generated DSL code"
date: 2026-09-18
theme: deterministic-boundaries
evidence: [21608ea83bf7c28c]
---
Irakli Betchvaia's **Typed Domain Grounding** embeds a domain-specific language inside a mainstream typed language, so the host **compiler and type checker**, not a second LLM pass, reject invalid generated output. He evaluates it on kUML benchmarks and an infrastructure-as-code example with generate-compile-repair loops.

For code generation, the cheapest verifier is often a compiler you already have.
