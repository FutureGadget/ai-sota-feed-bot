---
name: add-source
description: Add a new content source to the ai-sota-feed-bot feed end-to-end and prove it actually reaches readers. Use whenever adding/removing/re-tuning a source in config/sources.yaml, because adding a source there alone does NOT expose it — it must clear the ranking gates (slot mapping, freshness window, pool cap, slot caps, merge, top band). Walks the gates, makes the config edits, and validates with scripts/validate_source.py.
---

You are wiring a new source into the feed. The trap this skill exists to
prevent: **adding a source to `config/sources.yaml` only makes the collector
*fetch* it — it does not put it in the feed.** A source can be collected
perfectly and still be invisible to readers because it never clears the ranking
gauntlet. (This is exactly what happened to the Google Cloud blog: its posts
were collected for weeks, but a genuinely on-mission post — "Introducing the
Open Knowledge Format" — never appeared, dropped first by the global pool cap
and then unable to win a shared "vendor" slot.)

Do the steps in order. Step 4 (validate) is mandatory — never call a source
"added" without it printing `✅ EXPOSED`.

## The exposure gauntlet (understand this first)

Every item runs this gauntlet (`pipeline/ranking.py`); any gate drops it
silently. Full reference: `docs/ranking-v2-flow.md` → "Why a source may not
reach the feed".

1. **Collection / health** — must be in `config/sources.yaml`; `source_health`
   reliability ≥ 0.3 or the circuit breaker drops it (`health_floor`).
2. **Slot mapping** — a source not listed in any `slots.*.sources` falls into
   the `overflow` slot (base_bias −0.20, max 3) and almost never surfaces.
   **Mapping to a slot is a required, separate step from `sources.yaml`.**
3. **Per-slot freshness window** (`freshness_hours`) — older items dropped
   (`freshness_window`).
4. **Candidate pool cap** (`candidate_pool_cap`) — global top-N by
   `freshness + reliability`, with **slot-scaled decay** (`freshness_hours/3`).
   Short-window slots (vendor/cloud, 96h) decay ~2.5× faster than frontier
   (240h), so fresh short-window posts can be crowded out (`pool_cap`).
5. **Slot caps** (`max_items`, `max_per_source`) — slot may be full of
   higher-scored items.
6. **Global merge** (`max_items` 24) — per-slot `min_items` floors first, then
   headroom by `global_score` (`final_score + slot_priority`).
7. **Top-band constraints** — reorders (never drops) the visible top N.

## 1. Add the source to `config/sources.yaml`

Pick the `type` and required fields:

| type | fields | use for |
|---|---|---|
| `rss` | `url` | RSS/Atom feeds; GitHub releases (`.../releases.atom`); Google News search RSS |
| `sitemap` | `url`, `include_prefixes`, `extract_published_from_page`, `page_meta_cache_ttl_hours` | sites with no clean RSS (filter URLs by path prefix) |
| `arxiv_api` | `category`, `max_results` | arXiv categories |

```yaml
  - name: my_new_source        # unique; this name is the key everywhere else
    type: rss
    url: "https://example.com/feed.xml"
```

## 2. Map it to a ranking slot (the step people forget)

Edit **`config/ranking.yaml`** (authoritative; deep-merged over the preset)
**and** the active preset **`config/presets/balanced.yaml`** (keep them
coherent — `ranking.yaml` sets `preset: balanced`). Lists are overwritten, not
merged, so the source must appear in `ranking.yaml`'s slot list to count.

Add the source name to the `sources:` list of the best-fit existing slot:

- `frontier_official` — frontier-lab official blogs (OpenAI/Anthropic/DeepMind)
- `agent_tooling_releases` / `infra_runtime_releases` — GitHub release feeds
- `vendor_general_updates` — promotional vendor blogs (capped at 1; "noise" bucket)
- `cloud_platform_updates` — platform-eng vendor content (specs/standards)
- `practitioner_analysis` — practitioner blogs / analysis
- `community_signal` — HN / news-search aggregators
- `research_watch` — arXiv / papers / research blogs

**Creating a NEW slot?** Also add a `dynamic_slot_rerank.base_bias.<slot>`
entry — a missing entry defaults to `0.0`, which out-prioritizes most existing
slots and over-exposes the source. Set `min_items`/`max_items`/`max_per_source`/
`freshness_hours`/`blend` deliberately (mirror a sibling slot).

## 3. Position it with `source_bias` (recommended)

Add `source_bias.my_new_source: <delta>` in both files. Negative pushes it down
relative to peers, positive lifts it. Look at neighbors in the same slot for
scale (typically −0.35 … +0.40).

## 4. Validate end-to-end (mandatory)

```bash
python .agents/skills/add-source/scripts/validate_source.py --source my_new_source
# Track one specific item you expect to see:
python .agents/skills/add-source/scripts/validate_source.py \
    --source my_new_source --url-contains some-article-slug
```

It reports, for the source: slot mapping (warns if UNMAPPED), collected count,
which items pass prefilter (and the exact drop reason for those that don't —
`freshness_window` / `pool_cap` / `health_floor`), and which reach the final
feed. It prints `✅ EXPOSED` (exit 0) or `❌ NOT EXPOSED` with the likely fix
(exit 1), so it can also gate CI / a pre-merge check.

It scores against `data/tier1/latest.json` by default, so the source's items
must already be in a collected snapshot. If you just edited `sources.yaml` and
the source has never been collected, run the collector first:
`python collectors/collect.py` (then `pipeline/build_tier1.py`), or point
`--items` at a snapshot that contains it.

If the verdict is `❌ NOT EXPOSED`, apply the printed fix (commonly: map it to a
slot; raise `candidate_pool_cap` or move it to a longer-window slot if it dies
at `pool_cap`; raise the slot's `max_items` / lift `source_bias` if it loses the
slot) and re-run until `✅ EXPOSED`.

## 5. Document + commit

- Add an ADR entry to `docs/design-docs/decision-log.md` (date, decision,
  rationale, impact, rollback) for any non-trivial slot/cap change.
- If you added or substantially re-tuned a slot, update `docs/ranking-v2-flow.md`.
- Commit config/docs separately from runtime data
  (`scripts/git_commit_code.sh`, not `git_commit_runtime.sh`).
- Do **not** commit the regenerated `data/` from validation runs — the hourly
  pipeline owns runtime data.

## Quick reference: symptom → gate → fix

| Symptom (from validate_source.py) | Gate | Fix |
|---|---|---|
| `slot mapping: overflow ⚠️ UNMAPPED` | 2 | add to a slot's `sources:` |
| collected 0 | 1 | check `sources.yaml` name/url/type; run collector |
| DROP `freshness_window` (all items) | 3 | raise slot `freshness_hours`; or low-volume source only shows when fresh |
| DROP `pool_cap` | 4 | raise `candidate_pool_cap`; or longer-window slot |
| DROP `health_floor` | 1 | inspect `data/health/source_health.json`; source is flaky |
| passes pool, not in feed | 5–6 | raise slot `max_items`/`max_per_source`; lift `source_bias`; or own slot |
