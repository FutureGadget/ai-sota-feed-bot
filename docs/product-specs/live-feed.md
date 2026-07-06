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

## Feed aging

The default live feed can show a 7-day window without treating every eligible
story as equally current. The ranking pipeline applies a smooth time-decay
multiplier after normal relevance/source/topic scoring, so an article gradually
loses ordering power as it ages instead of staying at its original rank until
the freshness window expires.

Decay is configured in `config/ranking.yaml` (`time_decay.*`) and may vary by
slot for slower-moving surfaces such as research or practitioner analysis. It
does not change date filtering, `first_seen`, "New since your last visit", or
the user's ability to widen the time range.

## Editor's Desk inserts

Editor's Desk notes may appear between ranked feed items when another site
surface helps the reader understand the story they are already reading. These
are editorial utility inserts, not generic cross-promotion.

Rules:

- No Editor's Desk insert appears before the early ranked stories.
- At most two Editor's Desk inserts appear in one feed render.
- Inserts are dismissible for the current browser session.
- Storyline inserts explain a followed/developing thread.
- Playbook inserts require a source-backed card for the surrounding story.
- Daily recap inserts are allowed only when the latest recap is fresh and
  unread.
- Knowledge map and Foundations should appear only when a story maps to a
  concrete topic/concept, not as generic destination ads.

## "New since your last visit"

The **New** badge, the meta-line "N new since your last visit" count, and the
"⚡ Catch me up" brief all share one definition: an item is new when it
**entered the reader's feed** after their previous visit. That is keyed off
`first_seen` (the feed-arrival time the feed API computes in history mode — the
`run_at` when the item first reached the ranked window), falling back to
`published` only when `first_seen` is absent (the no-history "latest" API path).
Publish time alone is the wrong signal: the pipeline surfaces arXiv papers, slow
RSS, and resurfaced stories days after their publish date, so keying off
`published` silently drops items that are genuinely new to the feed. Card
display dates, storyline day numbering, and Saved snapshots still show
`published` first — those answer "when was this written", not "is this new to
me".

## Behavioral invariants

- Existing date ranges, topic pinning, search, Saved items, feedback, sharing,
  onboarding, catch-up, storyline notices, and reader-tuning behavior remain.
- `total_items` and `has_more` determine whether completion may be claimed.
- Local preview may read `data/processed/latest.json` when `/api/feed` is not
  available; production continues to use the API.
- Controls retain visible focus and 44 px targets. Reduced-motion preferences
  are respected.
