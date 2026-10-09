# Live feed front page (layout experiment)

Status: experiment, 50/50 split, started 2026-10-09.
Decision record: `docs/design-docs/decision-log.md` (2026-10-09, "Front-page
layout for the Brief, as a measured experiment").

## What it is

An alternative reading of the **same ranked Brief**, set like a newspaper front
page. Ranking, item selection, and order are identical in both arms. Only the
layout changes.

| Element | Front page | Ledger (control) |
|---|---|---|
| Palette | Warm paper with an ink-red accent; a matching dark variant | Cool blue-gray |
| Masthead | Centered serif "The AI brief that ends.", kicker visible, double rule above the lens controls | Left-aligned condensed sans |
| Edition strip | Date · Morning/Afternoon/Evening/Late edition (local time of the latest run) · "One ranking for every reader" | none |
| Rank 1 | **Lead**: large serif headline, drop-cap summary, left 58% column | Ledger card |
| Ranks 2-3 | **Secondaries**: beside the lead, 2-line summary | Ledger cards |
| Ranks 4-5 | **Pair**: side by side under a full rule | Ledger cards |
| Rank 6+ | Ledger cards (serif headlines) under a "The rest of the brief" rule | Ledger cards |
| Model Radar rail | Boxed module with a ruled caps heading | Open rail |

Front-page cards replace the rank column with a kicker (`01 PRACTITIONER
ANALYSIS`, from the item's ranking slot) and set the byline row (source, time,
badges, save/share/hide) under the summary. The ranked-because line stays
visible as a one-line caption: transparency is not traded for calm. Thumbnails
are omitted on the front page only.

Screenshots of both arms: `docs/assets/feed-front-page-2026-10-09/`.

## When it renders

The front page renders only when **all** of these hold. Otherwise the arm
shows the ordinary ledger with the paper palette:

- the reader is in the `frontpage` arm,
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

## Assignment

`web/index.html` assigns the arm in a head script before first paint:

1. `?layout=frontpage` or `?layout=ledger` wins and is persisted (use this to
   preview either arm).
2. Otherwise the stored arm in `localStorage["feed_layout_v1"]` is reused.
3. Otherwise the reader is assigned `frontpage` with probability
   `FRONT_PAGE_ROLLOUT` (0.5) and the result is stored.
4. If storage is unavailable, the reader gets the requested arm or `ledger`.
   Readers without storage cannot be followed across visits anyway.

The arm is exposed as `html[data-feed-layout]` for CSS and as the
`feed_layout` PostHog super property (`window.__llmDigestSuperProps`, registered
by `web/posthog-client.js` before `identify`). PostHog persists super
properties, so later events on other pages also carry the arm.

## Measurement

The north-star metric (`docs/status/north-star-metric.md`) decides this
experiment: **weekly returning readers**, compared as a returning rate per arm.
A sketch for the PostHog SQL editor (not yet run against production data):

```sql
WITH weekly AS (
  SELECT distinct_id,
         properties.feed_layout AS arm,
         toStartOfWeek(timestamp, 1) AS week
  FROM events
  WHERE event = '$pageview'
    AND properties.feed_layout IN ('frontpage', 'ledger')
    AND timestamp >= toDateTime('2026-10-12')
  GROUP BY distinct_id, arm, week
)
SELECT cur.week, cur.arm,
       count() AS readers,
       countIf(prev.distinct_id != '') AS returning_readers,
       round(returning_readers / readers, 3) AS returning_rate
FROM weekly cur
LEFT JOIN weekly prev
  ON prev.distinct_id = cur.distinct_id
 AND prev.arm = cur.arm
 AND prev.week = cur.week - INTERVAL 7 DAY
GROUP BY cur.week, cur.arm
ORDER BY cur.week, cur.arm
```

The first full week with the property everywhere is the week of 2026-10-12.
Score completed weeks only, starting with 2026-10-19 (the first week that has a
tagged previous week).

Guardrails, from events the feed already emits, normalized per reader:
`item_feedback` (the front page makes feedback hover-revealed), `click` (story
opens), and `item_hide`.

Decision rule: after at least four scored weeks, keep the front page if its
returning rate is not below the ledger's and feedback per reader has not fallen
by more than a third. Otherwise remove it. Promoting or removing it means setting
`FRONT_PAGE_ROLLOUT` to 1 or 0 **and** renaming the storage key
(`feed_layout_v1` → `feed_layout_v2`), because stored arms otherwise persist.
The unused styles can then be deleted in a follow-up. Carrying the look to `/daily` (Phase 2) waits on that result.

## Out of scope (Phase 1)

- `/daily`, `/weekly`, and other generated pages (`render_static_pages.py`):
  unchanged.
- The Korean feed shell (`web/ko/index.html`): unchanged.
- Web fonts: system serif stacks only (Iowan Old Style/Charter/Georgia; Bodoni
  or Didot for the display face where installed). No new font download.
- The crawler/no-JS feed seed: unchanged.
