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
4. **Finish line** - the curated Brief ends with a caught-up marker; over-cap
   stories remain available under the "More from ..." fold.

The first five Brief stories are set as a newspaper front page (lead, two
secondaries, a pair) before the ledger continues. Ranking and item selection
are unchanged; the API supplies the stable admission order, and the top five
are source-balanced. Contract: `feed-front-page.md`.

Ranking diagnostics such as `Matches feed focus:` are internal explanations,
not reader-facing editorial “why it matters” copy. Genuine significance text
may appear as supporting context.

### Lens semantics

Brief contains every eligible ranked item except release notes. Releases
are identified by the ranking pipeline's deterministic item type; a stale or
heuristic `llm_category` must not keep an inferred release in Brief. Strong
release markers are structural and opening-scoped (for example, a cleaned
summary beginning with `Release:` or `Release notes:`). An incidental mention
of a release later in an analysis article does not change its type. The feed
API applies the same opening-marker check to durable historical items so older
`news`/`platform` records move from Brief to Releases without rewriting history.

The Brief excludes every release item. `pipeline/release_policy.py` still
classifies releases as `major` or `minor` to order the Releases lane (a
substantive changelog ranks above a bare version bump); the tier never makes
an item Brief-eligible. Items from older snapshots without a tier behave the
same way.

## Rolling 24-hour window and stable order

The default Brief covers the last 24 hours by feed arrival (`first_seen`), not
the reader's local calendar day. A slow RSS post or arXiv paper published
yesterday but admitted this morning is part of today's brief, and the window
does not reset to empty at midnight. Published dates remain the card display
date and the key for `/daily/<date>`, `/weekly/<week>`, and custom date ranges.

Within that window the served pool is append-only. `api/feed.js` accumulates
every run snapshot, orders a story by the score it had when it FIRST entered
the feed, and never evicts a story because a later run stopped re-selecting
it. A new story enters by its own admission score. This keeps a refresh from
removing or reshuffling cards the reader is already looking at.

Editorial caps (`config/editorial.yaml` `caps` / `role_totals`) are flood
guards for the top of the brief, not a ceiling on the window. Cap-compliant
stories come first; over-cap stories continue below a "More from ..." fold and
remain one click away. The default Brief is the cap-compliant mix with an
explicit finish line; `All` and the section lenses show the full pool.

The top five are rebalanced so one source cannot take more than three of the
five front-page slots. The rest of the order is untouched by that pass.

### Admission ledger

The 24h Brief is served from `data/brief/<UTC date>.json`, not from the run
snapshots. `pipeline/brief_ledger.py` reads the day's judged pool and admits
one card per story when it first passes:

- **Gate:** a judge score at or above 0.35 (the judge's keep band), or an
  unjudged item with at least 300 characters of evidence. The judge's review
  band sits below the keep threshold, so reviews are not admitted. Releases are admitted by release tier
  (the judge drops release notes by design). Off-topic is rejected. When the
  judge is unavailable and no evidence field exists, the item fails open
  (the feed must not empty when Jev is down); present-but-thin evidence is
  still rejected.
- **Flood guards:** at most 3 admissions per source in any six-hour window,
  per-role daily caps (research 28, first-party 28, practitioner 18, community
  16, release 12, search 4, aggregator 4), and 120 admissions per UTC day.

Admission uses the deck selector's utility (judge score, platform relevance,
coverage, source tune, in-edition) plus freshness evaluated at admission and a
major-release must-cover bonus. Once admitted, a story keeps its card and
position for the window; later builds update coverage and `last_seen`, never
remove it. A story is not re-admitted within 24 hours of its previous
admission. The feed API keeps the latest admission when a story spans two
ledger files, then applies the display caps and front-page balance.

The run snapshots remain the source for calendar ranges (`Last 3d/7d/30d`,
explicit dates) and for the fallback when no ledger exists yet. The
crawler/no-JS feed seed is an edition snapshot, not the ledger; ledger-only
stories are reachable through their `/story` pages and the sitemap. Time decay
still shapes the run ranking; admission freezes freshness at the moment the
story enters the ledger, so a story does not lose its seat as it ages.

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
**entered the reader's feed** after their previous visit. The catch-up band is
collapsed by default; expanding it is the reader's choice and does not move
the stable body below. The definition is keyed off `first_seen` (the ledger
admission time on the default 24h path, or the `run_at` when the item first
reached the ranked window on calendar paths), falling back to `published` only
when `first_seen` is absent (the no-history "latest" API path). Publish time alone is
the wrong signal: the pipeline surfaces arXiv papers, slow RSS, and resurfaced
stories days after their publish date, so keying off `published` silently drops
items that are genuinely new to the feed. Card display dates, storyline day
numbering, and Saved snapshots still show `published` first - those answer
"when was this written", not "is this new to me".

## Behavioral invariants

- Existing date ranges, topic pinning, search, Saved items, feedback, sharing,
  onboarding, catch-up, storyline notices, and reader-tuning behavior remain.
- `total_items` and `has_more` determine whether completion may be claimed.
- A refresh inside the window never removes an admitted story. Over-cap
  stories remain in `items` with `beyond_cap: true` under the fold.
- Local preview may read `data/processed/latest.json` when `/api/feed` is not
  available; production continues to use the API.
- Controls retain visible focus and 44 px targets. Reduced-motion preferences
  are respected.

## Latest editorial content

The pre-story area shows up to three published editorial headlines with direct
links and source dates. When Catch me up is present, these rows appear inside
that card; response order never chooses a competing promo owner. The separate
`/updates` collection offers Latest/Unread browsing across all publishers.
See `nav-update-indicators.md` for the producer and opened-version contract.
