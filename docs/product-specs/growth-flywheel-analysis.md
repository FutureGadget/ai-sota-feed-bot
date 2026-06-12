# Growth Flywheel Analysis (2026-06)

UX-research + product audit of llm-digest.com: what would benefit readers most
and compound into a growth flywheel. Based on the live site, the live
`/api/feed` payload, and the current codebase.

## TL;DR

The growth *machinery* is already unusually complete for a project this size:
share permalinks with OG tags, durable `/story/<sid>` SEO pages, a closed and
visible reader-feedback loop, multi-channel subscribe, saved items, topic
pinning, trending badges. What is thin is the *fuel* the machinery pumps:

- `why_it_matters` on live items is literally `"Matches feed focus: agent, eval."`
  (mechanical keyword echo — LLM enrichment is disabled).
- Summaries are raw scraped HTML, including boilerplate like
  `Article URL: … Comments URL: …` for HN items.
- The visible taxonomy is 5 coarse buckets (`platform/news/research/paper/release`),
  so "pin my topics" and label filtering can't express what readers actually
  follow (agents, inference, evals, MCP, GPUs…).

Every existing loop — shares, SEO story pages, the weekly recap, subscribe
conversion — multiplies whatever content quality feeds it. **The highest-ROI
move is therefore synthesis quality (cheap LLM enrichment), then spending that
quality on programmatic topic pages and an owned email digest.**

## The flywheel

```
better synthesis (why-it-matters, clean summaries, real topics)
      → story/topic/recap pages worth landing on
      → organic search + share traffic
      → more readers → more feedback + CTR signal
      → auto-tune + ranking improve the feed
      → better feed → more subscribers (email/Telegram/RSS)
      → daily returning readers → more signal → (loop)
```

Loops already instrumented end-to-end in PostHog: `impression_batch → click`,
`item_feedback → auto_tune → reader-boosted badges`, `item_share →
share_landing`, `subscribe_menu_open → subscribe_click`. Nothing new needs
inventing on the measurement side; the gaps are in content value and
re-engagement channels.

## Ranked recommendations

### 1. Re-enable cheap LLM enrichment — the fuel (highest reader value)

`config/llm.yaml` is `enabled: false`; the interfaces are kept as no-ops and
`docs/product-specs/llm-ranking.md` already specs the labeling pass. At
~50–150 items/day, a small model (Haiku-class) costs cents per day. Use it for
three things, in priority order:

1. **A real one-sentence `why_it_matters`** answering "what would a platform
   engineer do differently because of this?" This is the product's core promise
   (PRODUCT_SENSE.md: *"know what changed and what to act on"*) and currently
   its weakest artifact.
2. **Clean 2-line summaries** (strip source HTML/boilerplate; HN items
   currently show "Article URL / Comments URL" as their summary).
3. **A topic taxonomy** (~15–25 stable topics: agents, inference, evals, MCP,
   GPUs/hardware, RAG, safety, open models…). `matched_topics` keywords exist
   in the pipeline already; promote them into curated, reader-facing labels.

Why this is the flywheel keystone: it upgrades every downstream surface at
once — story pages become search-worthy, share unfurls become compelling,
the weekly recap gets better raw material, and topic pinning becomes
meaningful. Without it the other loops spin on thin content.

### 2. Topic hub pages + per-topic RSS — programmatic SEO + "follow your beat"

Build on #1's taxonomy and infra that already exists (`story_store.py`,
`render_static_pages.py`, sitemap):

- Static `/topic/<slug>` pages: recent stories for that topic, interlinked with
  `/story/<sid>` and recap pages; real title/meta/OG/JSON-LD like the other
  static pages.
- `/rss.xml?topic=<slug>` (or `/topic/<slug>/rss.xml`) so an engineer can
  follow just their beat.
- Wire "pinned topics" and the subscribe menu to these pages.

Reader benefit: platform engineers follow *areas*, not a firehose. Flywheel
benefit: each topic page is a durable, self-updating landing page targeting
queries like "MCP news" or "LLM inference news" — programmatic SEO that
compounds with zero marginal editorial effort. Internal links from topic pages
also lift story-page rankings.

### 3. Owned email digest — the retention channel that's missing

RSS and Telegram are niche channels for this audience; email is the default
re-engagement channel for working engineers. Today email is an optional
external signup URL (`DIGEST_EMAIL_SIGNUP_URL`), likely unset in production.

- Minimum: actually configure a Buttondown/RSS-to-email flow so the existing
  subscribe menu's email option appears, and make the **weekly recap** the
  newsletter — it is already newsletter-shaped, agent-written, and the site's
  highest-polish artifact.
- Better: a daily "top 5 + why it matters" email rendered from the digest
  pipeline (content already exists in `data/digest/`).
- Track conversion with the existing `subscribe_click` event (channel=email).

Flywheel: every subscriber is a guaranteed daily/weekly return visit, which
feeds clicks/feedback into auto-tune, and forwarded emails are a share loop.

### 4. Finish the catch-up brief — habit formation for returning readers

"What you missed since your last visit" is partially built in the frontend.
For a feed that updates hourly, the returning-reader question is *"is it worth
checking again?"* A 3-item catch-up brief at the top answers it instantly and
trains a daily check-in habit. Pair it with the existing `New` badges and
last-visit tracking that already exist in localStorage.

### 5. Quick wins (days, not weeks)

- **Recap pages lack engagement affordances**: `/weekly` and `/daily` have no
  share button, no save, no subscribe CTA beyond the footer — yet they are the
  most shareable artifacts. Add the 📤 share + 🔔 subscribe CTAs there.
- **Read time** on recap pages ("3 min read") — cheap trust signal.
- **Surface the feedback loop louder**: the "reader feedback boosted N
  sources" footer note is the site's most differentiating trust feature;
  promote it to a small banner on the feed and recap pages
  ("This feed is tuned by its readers — N sources boosted this month").
- **Strip summary boilerplate** even before LLM work (regex-level fix for HN
  "Article URL/Comments URL" pattern in `pipeline/enrich.py`).

## What to watch (existing instrumentation suffices)

| Question | Signal |
| --- | --- |
| Is synthesis better? | CTR per item (`click`/`impression_batch`), 👍-vs-🫧 ratio in `item_feedback` |
| Are topic pages working? | Organic landings on `/topic/*` (referrer in `page_view`), `labels_pin` usage |
| Is email converting? | `subscribe_click` channel=email; later, UTM-tagged return visits |
| Habit forming? | Return-visit frequency (PostHog retention on `feed_view`), catch-up brief interactions |

## Sequencing

1 → 5 (parallel quick wins) → 2 → 3 → 4. Item #1 gates the ceiling of
everything else; #2 and #3 convert that quality into acquisition and
retention respectively; #4 closes the habit loop.
