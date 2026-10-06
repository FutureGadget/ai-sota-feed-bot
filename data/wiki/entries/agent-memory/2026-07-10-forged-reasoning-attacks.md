---
title: "FARMA poisons an agent's remembered reasoning, not just its stored facts"
date: 2026-07-10
theme: memory-integrity
evidence: [dc1acd837d32b604]
also: [prompt-injection]
---
The **Forged Amplifying Rationale Memory Attack (FARMA)** targets an agent's stored reasoning history. It inserts forged reasoning traces in evasive language that bypasses keyword-based defenses, then amplifies them; the paper also studies defenses.

Memory poisoning extends from corrupting what an agent believes to corrupting how it argues for it. Any memory that stores rationales or tool-use history needs the same provenance controls as stored facts.
