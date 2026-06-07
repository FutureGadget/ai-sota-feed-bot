---
name: weekly-summary
description: Produce and post the weekly "What happened in AI this week" recap for ai-sota-feed-bot. Reads the week's unique articles, summarizes and categorizes them, writes a recap JSON the /weekly page renders, validates it, and commits. Use this when running the weekly recap routine.
---

You are the editor of a weekly AI newsletter. Your job: turn one week of feed
articles into a reader-facing recap published at `/weekly`. The page renders
straight from a JSON file you write and commit — committing to the repo *is*
posting.

All scripts live next to this file in `scripts/` and can be run from anywhere
(they locate the repo root automatically).

## The routine (run in order)

### 1. Build the input bundle
```bash
python .agents/skills/weekly-summary/scripts/build_weekly_input.py
# Targets the ISO week containing today. Override with:
#   --week 2026-W23           (a specific ISO week, Mon–Sun)
#   --end 2026-06-07 --days 7 (a trailing window ending on a date)
#   --types news,release      (default: news only; use 'all' for everything)
```
This writes `data/weekly/input/latest.json` (and `input/<week>.json`) — the
week's unique, deduped articles. **This is your reading material.**

By default only `news`-type items are bundled (papers/releases are better
served by the live feed and add little to a weekly narrative). The bundle's
`included_types` field records what was included.

### 2. Check the week isn't already published (dedup)
The **unique key for a week is its ISO week id** (`YYYY-Www`, e.g. `2026-W23`) —
the same value used as the `week` field, the filename `data/weekly/<week>.json`,
and the index key. Read the `week` field from `data/weekly/input/latest.json`,
then check whether `data/weekly/<week>.json` already exists:

- **If it exists**, a recap for this week was already published. **Stop here** —
  do not overwrite or create a duplicate. Report that `<week>` is already done.
- **Only continue if it does not exist.**

(To intentionally regenerate a week, delete or explicitly overwrite that one
file — the index is keyed by week id, so there is always exactly one per week.)

### 3. Write the recap (your editorial work — only an agent can do this)
Read `data/weekly/input/latest.json`. Each entry in `articles[]` has:
`title`, `url` (original source link), `source`, `type`, `category`,
`summary`, `published`. The bundle also carries `week`, `start`, `end`,
`range_label`, `article_count`, and `category_hint` (default per-category counts).

Write `data/weekly/<week>.json` (e.g. `data/weekly/2026-W23.json`):
```json
{
  "week": "2026-W23",
  "start": "2026-06-01",
  "end": "2026-06-07",
  "title": "What happened in AI — Jun 1–7, 2026",
  "generated_at": "<ISO-8601 now>",
  "intro": [
    "Paragraph 1: the headline through-line of the week.",
    "Paragraph 2: the next thread.",
    "Paragraph 3 (optional): the kicker."
  ],
  "highlights": [
    "Scannable one-line takeaway (3–6 of these).",
    "Each is a standalone bullet — no need to read the intro to get the gist."
  ],
  "article_count": 144,
  "categories": [
    {
      "name": "Model & Product Releases",
      "slug": "model-product-releases",
      "summary": "1–2 sentences on what happened in this category.",
      "articles": [
        {
          "title": "…",
          "summary": "one tight line: what it is + why it matters",
          "source": "openai_blog",
          "url": "https://…  (copy verbatim from the bundle)",
          "published": "2026-06-03T17:44:18Z"
        }
      ]
    }
  ]
}
```

**Editorial guidance**
- **Preserve `url` exactly** from the bundle — it's the reader's link back to
  the source. Never invent, shorten, or guess links.
- Group thematically into 3–6 categories. The bundle is news-only and lands in
  a single "Industry News" bucket, so **you** define the themes — e.g. "Agents
  & Tooling", "Open Models", "Funding & Business", "Safety & Policy", "Research
  Highlights". Don't just echo "Industry News".
- Curate, don't dump. Skip duplicates and low-signal items; keep each category
  to its strongest ~5–10 articles. You need not include every article.
- `intro` is the headline experience — tell the reader what actually happened
  this week, newsletter-opener style. Use the array form (one string per
  paragraph) so the page renders it as readable paragraphs; a plain string still
  works and is split on blank lines. Keep it to 2–4 short paragraphs.
- `highlights` (optional but recommended) is a "In 30 seconds" bullet list the
  page renders above the intro — 3–6 scannable one-liners so a reader gets the
  gist without reading the full narrative. Cover the week's biggest threads.

### 4. Validate + rebuild the index (what the site serves)
```bash
python .agents/skills/weekly-summary/scripts/build_weekly_index.py
```
Validates every recap against the schema and rebuilds
`data/weekly/index.json` + `data/weekly/latest.json`. It exits non-zero on a
malformed recap — fix and re-run until clean. (`--check` validates without writing.)

### 5. Post it (commit + push)
```bash
git add data/weekly/
git commit -m "weekly recap: <week>"
git push
```

## Helpers
- `scripts/run_weekly.sh` — runs step 1 + (optionally) the placeholder seed +
  step 4 in one go, for smoke-testing the UI.
- `scripts/seed_weekly_sample.py` — deterministic **placeholder** recap from the
  input bundle. NOT a real summary; use it only as a schema example or to test
  the `/weekly` page rendering.

## Where it shows up
- Page: `/weekly` (latest) and `/weekly/<week>` (archive dropdown)
- API: `/api/weekly`, `/api/weekly?week=<week>`, `/api/weekly?list=1`
