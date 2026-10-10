# Live feed front page

Status: shipped as the only feed layout (2026-10-10).
Decision record: `docs/design-docs/decision-log.md` (2026-10-10, "Broadsheet
theme for every page; the feed front page replaces the ledger opening").
Site-wide palette and type: `docs/FRONTEND.md`, "Site theme".

## What it is

The Brief's first five stories are set like a newspaper front page. Ranking,
item selection and order are unchanged; only the presentation differs from the
rest of the list.

| Element | Treatment |
|---|---|
| Masthead | Centered serif "The AI brief that ends.", kicker line, double rule above the lens controls |
| Edition strip | Date · Morning/Afternoon/Evening/Late edition (local time of the latest run) · "One ranking for every reader" |
| Rank 1 | **Lead**: large serif headline, drop-cap summary, left 58% column |
| Ranks 2-3 | **Secondaries**: beside the lead, 2-line summary |
| Ranks 4-5 | **Pair**: side by side under a full rule |
| Rank 6+ | Ledger cards (serif headlines) under a "The rest of the brief" rule |
| Model Radar rail | Boxed module with a ruled caps heading |

Front-page cards replace the rank column with a kicker (`01 PRACTITIONER
ANALYSIS`, from the item's ranking slot) and set the byline row (source, time,
badges, save/share/hide) under the summary. The ranked-because line stays
visible as a one-line caption: transparency is not traded for calm. Thumbnails
are omitted on the front page only.

Screenshots: `docs/assets/feed-front-page-2026-10-09/` (the experiment
comparison) and `docs/assets/broadsheet-theme-2026-10-10/` (every page type).

## When it renders

The front page renders only when **all** of these hold. Otherwise the feed
shows the ordinary ledger:

- the Brief lens is active,
- no search query,
- at least 5 visible stories.

Saved, Platform/Research/Releases/News/All, and search views never use the front
page. Feed companions that would land inside it (first-visit prompt, subscribe
nudge, mobile Model Radar, Editor's Desk notes) move to just below the "rest of
the brief" rule. The finish line is unchanged.

## Interaction contract

Front-page stories are ordinary feed cards (`#list > article[data-item-key]`)
with an extra `fp-lead`/`fp-second`/`fp-pair` class. CSS floats reflow them
(`#list:has(> article.fp-lead)`); there is no wrapper element. Save, share, hide
with undo, swipe-to-hide, `j`/`k` selection, focus restoration, impressions and
click tracking therefore behave exactly as in the ledger.

On hover-capable devices the Useful / Not relevant / Hype row of a front-page
card appears on hover or keyboard focus, and stays visible once a vote is cast.
On touch devices it is always visible. The buttons are never removed from the
DOM or the tab order, because they feed `auto_tune`.

Below 860px the front page is a single column in rank order. At no width may it
add horizontal scrolling.

## Watching it

There is no A/B split; the owner chose the layout outright. Watch weekly
returning readers (`docs/status/north-star-metric.md`) across the change, and
`item_feedback` per reader, since feedback is hover-revealed on desktop front
page cards.

## Out of scope

- The crawler/no-JS feed seed keeps its plain list.
- Web fonts: system serif stacks only (Iowan Old Style/Charter/Georgia; Bodoni
  or Didot for the display face where installed). No new font download.
