# Agent Know-How — the knowledge universe (orbit view on /map)

**Status:** shipped 2026-08-05 · **Surfaces:** `/map` (orbit view + list), `/topic/<slug>` (read logging)

## Problem

The wiki's `/map` page was a flat obstacle→solution list labeled "Knowledge map".
Readers did not understand why it exists: "knowledge map" describes how we
manage the content internally, not what the reader gets. The clustering
(areas → obstacles → solutions) was invisible, nothing signaled what was new,
and nothing reflected what the reader had already absorbed.

## Positioning and naming

- User-facing name: **Agent Know-How** (nav label). Headline: *"The essential
  know-how for production-grade agents."* The term "knowledge map" no longer
  appears on reader-facing surfaces (nav, chips, breadcrumbs, OG cards, email).
- The weekly email section formerly "🗺️ New in the knowledge map" is now
  "🪐 New agent know-how" (`publish/publish_email.py`). Same selection logic.
- URLs are unchanged (`/map`, `/topic/<slug>`) — SEO and links keep working.

## The orbit view

A Three.js scene at the top of `/map` (module: `web/universe/universe.js`,
loaded lazily like the mascot; the existing obstacle→solution list stays below
as the no-JS/SEO/accessibility fallback).

- **Sun** = "your agent, in production" — everything orbits the one job.
- **Planet** = one wiki *area* (problem cluster). Position on its own orbit
  ring; size grows with page count.
- **Satellite** = one wiki *page* (obstacle or solution) circling its planet.
  A solution addressing obstacles in several areas appears around each such
  planet (counts in the HUD readout are deduplicated).
- **Read state** (local only): satellites of pages you have read are dim;
  unread ones glow. A planet's atmosphere glow scales with its unread share —
  the universe literally calms down as you work through it.
- **What's new**: pages updated in the last 21 days that you have not (re)read
  pulse and give the planet a radar-ping ring; the panel rows carry `NEW`
  (never read) / `UPDATED` (changed since you read it) badges with dates.
- **Interaction**: drag orbits, wheel/pinch zooms, click/tap a planet (or its
  satellites) focuses it and opens a contents panel (obstacles with their
  solutions, each linking to `/topic/<slug>`); Esc or ✕ closes; HUD has
  zoom +/− and reset. Hovering shows a tooltip (planet stats or page title).
- **Motion discipline**: render loop parks when the tab is hidden or the stage
  is off-viewport; `prefers-reduced-motion` disables ambient drift/pulses and
  renders only on interaction. Any boot failure (no WebGL, blocked CDN) hides
  the section entirely — the list below is the page.

## Data contract (unchanged for curators)

The orbit view is a pure *presentation* of the compiled wiki:

- `wiki-curator` skill, `config/wiki_schema.md`, `pipeline/build_wiki.py`, and
  `data/wiki/**` are untouched. The curation contract is exactly as before.
- `pipeline/render_static_pages.py::wiki_universe_data()` projects
  `data/wiki/index.json` (areas + nodes with title/kind/updated/solutions) into
  a small JSON data island inside the generated `web/map.html`; no API call.
- Scaling is automatic: a new area in the index becomes a new planet (next
  color slot, next orbit ring); a new node becomes a new satellite. Nothing to
  configure when knowledge grows.

## Read history (browser-local)

- `nav-updates.js` records `/topic/<slug>` visits (any locale prefix) into
  localStorage `ai_feed_topic_reads_v1` as `{slug: epoch_ms}`, capped at 500
  entries. Never sent anywhere; the orbit view reads it on load and on
  `storage` events (cross-tab live update).
- "Read" means read *since the page's last update*, so a page revision
  re-brightens its satellite.

## Telemetry

PostHog events (defensive no-ops): `universe_planet_open {area, unread,
fresh}`, `universe_topic_click {slug, area}` — enough to see whether the orbit
view drives topic reads (which feeds the weekly-returning-readers north star).

## Files

- `web/universe/universe.js` — the module (hand-edited, portable, defensive)
- `pipeline/render_static_pages.py` — data island + mount + hero/naming + CSS
- `web/nav-updates.js` — read logging + chip label
- `publish/publish_email.py` — weekly email section rename
