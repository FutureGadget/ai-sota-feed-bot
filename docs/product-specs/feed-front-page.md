# Live feed front page

Status: shipped as the only feed layout (2026-10-10); simplified the same day.
Decision records: `docs/design-docs/decision-log.md` (2026-10-10, "Broadsheet
theme for every page; the feed front page replaces the ledger opening" and
"Quieter feed front page: a headline and one source line per story").
Site-wide palette and type: `docs/FRONTEND.md`, "Site theme".

## What it is

The Brief's first five stories are set like a newspaper front page. Ranking
and item selection are unchanged; the API supplies a stable admission order,
and a top-band pass keeps one source from taking more than three of the five
slots. Only the presentation differs from the rest of the list. Each story
reads as a headline plus one source line; only the lead carries a standfirst. The standfirst is `summary_1line`; when that
echoes the title or is empty, the lead uses the first sentence of the Jev
`content_excerpt` (HN link posts often need this).

| Element | Treatment |
|---|---|
| Masthead | Left-aligned Geist "The daily paper for AI engineers." with the status line (story count, last update) set small on the right (below it on phones). No kicker or promise line. A 1px rule above the lens controls; the active lens is a filled pill |
| Filter chips | Hidden on the default Brief; shown only for a non-default lens or pinned topics |
| Editor's Desk strip | Red sentence-case heading and three headlines in columns (one column on phones), no box, no summaries |
| Section heading | "Front page" on the left in small semibold type; date · Morning/Afternoon/Evening/Late edition on the right in Geist Mono; 1px rule |
| Rank 1 | **Lead**: kicker (`01 Agent engineering`: red mono rank, sentence-case category from the judge), large tight Geist headline, muted standfirst with no drop cap, left 58% column |
| Ranks 2-5 | **Headlines**: numbered, beside the lead, headline and source line only (three headlines when the Brief has exactly four stories) |
| Rank 6+ | The same headline cards under "The rest of the brief" (with the curated remainder count) |
| Pool fold | After the last cap-compliant story: "More from the past 24 hours" plus a Show/Hide control for the over-cap pool |
| Model Radar rail | 1px bordered, 12px-radius module with a sentence-case heading |
| Reader-tuning note | A footnote under the finish line, not a banner above the list |

### Story cards

Every card in the list, front page or not, is:

- the headline (Geist semibold), with a small Geist Mono rank to its left, then
- one source line: source (muted), time, type and New badges, the
  storyline badge, then ☆ save and a "⋯" button.

"⋯" opens a small panel holding everything a reader wants once: Share, Hide,
the ranked-because line, the fresh/trend/boost signals, "Also covered by", and
the Useful / Not relevant / Hype row. One panel is open at a time; an outside
click or Escape closes it (Escape returns focus to "⋯"). A vote from an email
link opens the panel of the voted card. Thumbnails are not shown.

The Korean feed (`/ko/`) has no panel: its front-page cards show the source
line (source, date, New, storyline) and drop the ranking signals; the lead
keeps its summary.

Screenshots: `docs/assets/feed-front-page-2026-10-09/` (the experiment
comparison), `docs/assets/broadsheet-theme-2026-10-10/` (every page type) and
`docs/assets/feed-simplified-2026-10-10/` (the broadsheet layout), and
`docs/assets/ui-framework-migration/front-precision-*.jpg` (the current
Precision styling, 2026-11-07).

## When it renders

The front page renders only when **all** of these hold. Otherwise the feed
shows the ordinary ledger:

- the Brief lens is active,
- no search query,
- at least 4 visible stories.

The five stories come from the stable pool for the selected window. A refresh
does not reshuffle them unless a newly admitted story's score enters the top
band; the body below stays in place.

Five stories is the full layout: a lead plus four headlines. With exactly four,
the front page renders as a lead plus three headlines and the "rest of the
brief" heading is omitted. Fewer than four falls back to the ordinary ledger,
which is clearer than a front page with too little to fill it.

Saved, Platform/Research/Releases/News/All, and search views never use the front
page; they use the same headline cards. Feed companions that would land inside
it (first-visit prompt, subscribe nudge, mobile Model Radar, Editor's Desk
notes) move three stories past the "rest of the brief" heading, so nothing
interrupts the front page or the heading. The finish line is unchanged.

## Interaction contract

Front-page stories are ordinary feed cards (`#list > article[data-item-key]`)
with an extra `fp-lead`/`fp-second` class. CSS floats reflow them
(`#list:has(> article.fp-lead)`); there is no wrapper element. Save, share, hide
with undo, swipe-to-hide, `j`/`k` selection, focus restoration, impressions and
click tracking therefore behave exactly as in the ledger.

The Useful / Not relevant / Hype buttons live in the "⋯" panel on every card.
They stay in the DOM (inside the closed `<details>`), because they feed
`auto_tune`.

Below 860px the front page is a single column in rank order. At no width may it
add horizontal scrolling.

## Watching it

There is no A/B split; the owner chose the layout outright. Watch weekly
returning readers (`docs/status/north-star-metric.md`) across the change, and
`item_feedback` per reader, since feedback now sits one tap away behind "⋯".
If votes per reader drop sharply, bring the row back onto the lead card first.

## Out of scope

- The crawler/no-JS feed seed keeps its plain list.
- Web fonts: system serif stacks only (Iowan Old Style/Charter/Georgia; Bodoni
  or Didot for the display face where installed). No new font download.
