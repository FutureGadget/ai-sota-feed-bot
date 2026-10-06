---
title: "Counting compute flips a hallucination leaderboard ranking"
date: 2026-07-28
theme: score-validity
evidence: [9f5bc06695260c32]
---
"The Cost of Knowing" (MAS-HQ) normalizes factuality scores for the compute spent producing them. A brute-force **best-of-4** agent posts the higher raw score (H-Score 0.9169 vs 0.9103) and would top a static leaderboard, but loses on cost-normalized Q-Score (**0.5169 vs 0.5217**) at roughly four times the tokens and latency.

Static leaderboards treat compute as free. The system that tops one can be the worse one to deploy; see [agent cost](/topic/agent-cost).
