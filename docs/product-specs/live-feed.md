# Live feed UX contract

The Live feed answers one question: **what is worth reading now?** It is a
ranked, finite brief for platform and agent engineers—not an infinite stream.

## Reading hierarchy

1. **Promise and coverage** — the current range, story count, and freshness.
2. **Lens controls** — Brief is the default; Platform, Research, Releases,
   News, All, and Saved remain explicit alternatives.
3. **Ranked ledger** — each visible story has a rank, source/date evidence,
   headline, concise summary, optional genuine editorial context, and feedback
   controls.
4. **Finish line** — only shown when the selected Brief range is complete.

Ranking diagnostics such as `Matches feed focus:` are internal explanations,
not reader-facing editorial “why it matters” copy. Genuine significance text
may appear as supporting context.

## Behavioral invariants

- Existing date ranges, topic pinning, search, Saved items, feedback, sharing,
  onboarding, catch-up, storyline notices, and reader-tuning behavior remain.
- `total_items` and `has_more` determine whether completion may be claimed.
- Local preview may read `data/processed/latest.json` when `/api/feed` is not
  available; production continues to use the API.
- Controls retain visible focus and 44 px targets. Reduced-motion preferences
  are respected.
