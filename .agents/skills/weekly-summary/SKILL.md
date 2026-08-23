---
name: weekly-summary
description: Produce and post the weekly "What happened in AI this week" recap for ai-sota-feed-bot. Reads the week's unique articles, summarizes and categorizes them, writes a recap JSON the /weekly page renders, validates it, and commits. Use this when running the weekly recap routine.
---

You are the editor of a weekly AI newsletter. Your job: turn one week of feed
articles into a reader-facing recap published at `/weekly`. The page renders
straight from a JSON file you write and commit — committing to the repo *is*
posting.

Prose bar: every field you write below (`intro`, `highlights`, category
`summary`, article `summary`) follows `.agents/skills/writing-style/SKILL.md`
— BLUF, one idea per paragraph, scannability, specifics over generalities.

All scripts live next to this file in `scripts/` and can be run from anywhere
(they locate the repo root automatically).

## The routine (run in order)

### 1. Build the input bundle
```bash
python .agents/skills/weekly-summary/scripts/build_weekly_input.py
# Targets the ISO week containing today. Override with:
#   --week 2026-W23           (a specific ISO week, Mon–Sun)
#   --end 2026-06-07 --days 7 (a trailing window ending on a date)
#   --types news,release      (default: news,release,research,paper)
#   --keep-carryover          (include articles published in an earlier week
#                              but still in the feed; OFF by default)
#   --no-prior-dedup          (don't exclude articles already in an earlier
#                              week's recap; dedup is ON by default)
```
This writes `data/weekly/input/latest.json` (and `input/<week>.json`) — the
week's unique, deduped articles. **This is your reading material.**

Because articles linger in the live feed for several days, the bundle is
filtered so a recap only covers what is genuinely new *this* week and never
repeats a prior week:

- **Published-this-week** — an article is included only if its own `published`
  date falls inside the week window, not merely because it was still being
  collected this week (`published_window` in the bundle).
- **Cross-week dedup** — any article URL already published in an earlier week's
  recap is dropped (`prior_recap_dedup` / `prior_recap_urls` in the bundle).

(Override either with the flags above only if you deliberately want carryover.)

By default `news`, `release`, `research`, and `paper` items are bundled.
Releases and papers belong only when they support a real weekly shift or a
concrete builder action; curate them hard rather than dumping them into the
published recap. Each article carries `source_sid` and `playbook_card_id` when
the preceding Playbook run produced a validated source-backed card for that
exact URL.

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
`summary`, `published`, plus optional `publisher_name` and `publisher_domain`.
The bundle also carries `week`, `start`, `end`,
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
    "Paragraph 1: the dominant shift and what changed.",
    "Paragraph 2: how the other major patterns connect.",
    "Paragraph 3 (optional): the durable implication."
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
          "publisher_name": "Bloomberg",
          "publisher_domain": "bloomberg.com",
          "url": "https://…  (copy verbatim from the bundle)",
          "published": "2026-06-03T17:44:18Z"
        }
      ]
    }
  ]
}
```

**Editorial guidance**
- When an input article has `publisher_name` or `publisher_domain`, copy those
  fields verbatim into the recap article. Omit them when absent.
- **Preserve `url` exactly** from the bundle — it's the reader's link back to
  the source. Never invent, clean, normalize, shorten, or guess links. Skip an
  item whose only supplied URL is an ugly redirect or tracking URL rather than
  rewriting it.
- Group thematically into 3–6 categories. The bundle is news-only and lands in
  a single "Industry News" bucket, so **you** define the themes — e.g. "Agents
  & Tooling", "Open Models", "Funding & Business", "Safety & Policy", "Research
  Highlights". Don't just echo "Industry News".
- Curate, don't dump. Skip duplicates and low-signal items; keep each category
  to its strongest ~5–10 articles. You need not include every article.
- `intro` is the editorial interpretation beside the week's signal list. Explain
  the dominant shift, connect the other major patterns, and end with the durable
  implication in 2–3 short paragraphs, ideally under 1,100 characters total.
  Use the array form (one string per paragraph); a plain string still works and
  is split on blank lines. Do not walk through every category in order.
- `highlights` (optional but recommended) is a "In 30 seconds" bullet list the
  page renders above the intro — 3–6 scannable one-liners so a reader gets the
  gist without reading the full narrative. Cover the week's biggest threads.
- Treat each category as a **weekly shift**, not a storage bucket. Its `summary`
  should make one clear pattern claim that the listed articles then support.
  Avoid vague labels such as "Other news" or categories defined only by source.
- Never author or copy `problem`, `apply`, or `result` into recap JSON. Inline
  Playbook takeaways are overlaid deterministically after validation.

### 4. Validate + rebuild the index (what the site serves)
```bash
python .agents/skills/weekly-summary/scripts/build_weekly_index.py
```
Validates every recap against the schema and rebuilds
`data/weekly/index.json` + `data/weekly/latest.json`, then re-renders the
static `/weekly/<week>` pages + sitemap (`web/weekly/`, `web/sitemap.xml`) via
`pipeline/render_static_pages.py`. It exits non-zero on a malformed recap —
fix and re-run until clean. (`--check` validates without writing.)

### 5. Post it (commit + push)
```bash
git add data/weekly/ web/weekly/ web/sitemap.xml web/robots.txt
# Pin the agent identity so the commit signature can't inherit the machine's
# ambient git config (sets both author and committer).
git -c user.name="Claude" -c user.email="noreply@anthropic.com" \
  commit -m "weekly recap: <week>"
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
