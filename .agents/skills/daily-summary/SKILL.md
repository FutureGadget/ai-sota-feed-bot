---
name: daily-summary
description: Produce and post the daily "What happened in AI today" recap for ai-sota-feed-bot. Reads the day's unique articles, summarizes and categorizes them, writes a recap JSON the /daily page renders, validates it, and commits. Use this when running the daily recap routine.
---

You are the editor of a daily AI newsletter. Your job: turn one day of feed
articles into a reader-facing recap published at `/daily`. The page renders
straight from a JSON file you write and commit — committing to the repo *is*
posting.

Prose bar: every field you write below (`intro`, `highlights`, category
`summary`, article `summary`) follows `.agents/skills/writing-style/SKILL.md`
— BLUF, one idea per paragraph, scannability, specifics over generalities.

All scripts live next to this file in `scripts/` and can be run from anywhere
(they locate the repo root automatically). This routine mirrors the
`weekly-summary` skill, but the unit is a single calendar day (`YYYY-MM-DD`)
instead of an ISO week.

## The routine (run in order)

### 1. Build the input bundle
```bash
python .agents/skills/daily-summary/scripts/build_daily_input.py
# Targets the next unprocessed UTC day (one day past the latest published
# recap or confirmed-empty day in data/daily/state.json; prints "due": false
# and writes nothing until that date has arrived in KST — the routine's own
# 06:00 KST publish clock, not the UTC calendar). Override with:
#   --date 2026-06-07         (a specific calendar day; never touches state.json)
#   --days 1                  (lookback window ending on --date; default 1)
#   --types news,release      (default: news only; use 'all' for everything)
#   --keep-carryover          (include articles published on an earlier day
#                              but still in the feed; OFF by default)
#   --no-prior-dedup          (don't exclude articles already in an earlier
#                              day's recap; dedup is ON by default)
```
This writes `data/daily/input/latest.json` (and `input/<date>.json`) — the
day's unique, deduped articles. **This is your reading material.**

Because articles linger in the live feed for several days, the bundle is
filtered so a recap only covers what is genuinely new *today* and never
repeats a prior day:

- **Published-today** — an article is included only if its own `published`
  date falls inside the day window, not merely because it was still being
  collected today (`published_window` in the bundle).
- **Cross-day dedup** — any article URL already published in an earlier day's
  recap is dropped (`prior_recap_dedup` / `prior_recap_urls` in the bundle).

(Override either with the flags above only if you deliberately want carryover.)

By default only `news`-type items are bundled (papers/releases are better
served by the live feed and add little to a daily narrative). The bundle's
`included_types` field records what was included.

### 2. Check the day isn't already published (dedup)
The **unique key for a day is its date id** (`YYYY-MM-DD`, e.g. `2026-06-07`) —
the same value used as the `date` field, the filename `data/daily/<date>.json`,
and the index key. Read the `date` field from `data/daily/input/latest.json`,
then check whether `data/daily/<date>.json` already exists:

- **If it exists**, a recap for this day was already published. **Stop here** —
  do not overwrite or create a duplicate. Report that `<date>` is already done.
- **Only continue if it does not exist.**

(To intentionally regenerate a day, delete or explicitly overwrite that one
file — the index is keyed by date id, so there is always exactly one per day.)

### 3. Write the recap (your editorial work — only an agent can do this)
Read `data/daily/input/latest.json`. Each entry in `articles[]` has:
`title`, `url` (original source link), `source`, `type`, `category`,
`summary`, `published`. The bundle also carries `date`, `range_label`,
`article_count`, and `category_hint` (default per-category counts).

Write `data/daily/<date>.json` (e.g. `data/daily/2026-06-07.json`):
```json
{
  "date": "2026-06-07",
  "title": "What happened in AI — Jun 7, 2026",
  "generated_at": "<ISO-8601 now>",
  "intro": [
    "Paragraph 1: the headline through-line of the day.",
    "Paragraph 2 (optional): the secondary thread or operational implication."
  ],
  "highlights": [
    "Scannable one-line takeaway (3–6 of these).",
    "Each is a standalone bullet — no need to read the intro to get the gist."
  ],
  "article_count": 24,
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
          "published": "2026-06-07T17:44:18Z"
        }
      ]
    }
  ]
}
```

**Editorial guidance**
- **Preserve `url` exactly** from the bundle — it's the reader's link back to
  the source. Never invent, shorten, or guess links.
- Do a category-design pass before writing JSON. Read all article titles and
  summaries, make a scratch grouping by what changed for platform/agent
  engineers, merge weak groups, split any bucket with more than about 5 items,
  then write only the final categories. The scratch grouping is not output.
- Group thematically into 3–6 categories. The bundle usually lands in one
  deterministic "Industry News" bucket, so **you** define the reader-facing
  themes. Prefer precise buckets from this lens when the day's evidence supports
  them:
  - Agent runtimes, orchestration, memory, tool use, or MCP
  - Evals, observability, reliability, testing, or benchmarks
  - AI infrastructure, inference, chips, cloud, data, or deployment
  - Security, safety, compliance, provenance, identity, or policy that changes
    engineering practice
  - Models, frontier-lab releases, open weights, or local execution
  - Developer tools, coding agents, SDKs, frameworks, or workflow automation
  - Business/adoption/funding only when it changes platform strategy, compute
    economics, or where builders should pay attention
- Treat each category as a pattern claim, not a storage bucket. The category
  `name` should tell the reader the lane; the `summary` should state the
  specific daily signal that the listed articles support. Avoid vague labels
  like "Other", "Misc", "Industry News", "Research Highlights" without a
  concrete angle, and avoid categories defined only by source/company.
- Curate, don't dump. Skip duplicates and low-signal items; keep each category
  to its strongest 2–5 items when possible. If an article does not strengthen a
  category's pattern, leave it out. You need not include every article.
- Order categories by reader value: agent/platform engineering practice first,
  then infra/model shifts, then security/policy, then business context. A major
  frontier-lab release can lead only when it is the day's dominant engineering
  story.
- `intro` is the synthesis beside the fast-scan highlights, not a second full
  recap. Tell the reader what actually happened today and connect the major
  signals in 1–2 short paragraphs, ideally under 650 characters total. Use the
  array form (one string per paragraph); a plain string still works and is split
  on blank lines. Do not restate every highlight or enumerate every category.
- `highlights` (optional but recommended) is a "In 30 seconds" bullet list the
  page renders above the intro — 3–6 scannable one-liners so a reader gets the
  gist without reading the full narrative. Cover the day's biggest threads.
- Never author or copy `problem`, `apply`, or `result` into recap JSON. When the
  Playbook routine already produced a validated card for an article,
  deterministic rendering may show it inline. Daily remains news-first; a
  Playbook match does not force an article into the recap.

### 4. Validate + rebuild the index (what the site serves)
```bash
python .agents/skills/daily-summary/scripts/build_daily_index.py
```
Validates every recap against the schema and rebuilds
`data/daily/index.json` + `data/daily/latest.json`, then re-renders the static
`/daily/<date>` pages + sitemap (`web/daily/`, `web/sitemap.xml`) via
`pipeline/render_static_pages.py`. It exits non-zero on a malformed recap —
fix and re-run until clean. (`--check` validates without writing.)

### 5. Post it (commit + push)
```bash
git add data/daily/ web/daily/ web/sitemap.xml web/robots.txt
# Pin the agent identity so the commit signature can't inherit the machine's
# ambient git config (sets both author and committer).
git -c user.name="Claude" -c user.email="noreply@anthropic.com" \
  commit -m "daily recap: <date>"
git push
```

## Helpers
- `scripts/run_daily.sh` — runs step 1 + (optionally) the placeholder seed +
  step 4 in one go, for smoke-testing the UI.
- `scripts/seed_daily_sample.py` — deterministic **placeholder** recap from the
  input bundle. NOT a real summary; use it only as a schema example or to test
  the `/daily` page rendering.

## Where it shows up
- Page: `/daily` (latest) and `/daily/<date>` (archive dropdown)
- API: `/api/daily`, `/api/daily?date=<date>`, `/api/daily?list=1`
