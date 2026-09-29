# Model Radar pricing and comparison investigation

Investigated September 29, 2026. This records the pre-implementation findings.
The adopted behavior is documented in the [pricing and comparison contract](../product-specs/model-radar-comparison.md).
The original concept is [Model Release Radar](model-release-radar.md).

Follow-up recommendation after comparing Portkey and OpenRouter: use OpenRouter
as the single automated source for prices and serving metadata, and retain
Artificial Analysis for evaluation scores. Use provider websites to resolve
reported discrepancies during investigation, not as dependencies of the
scheduled collector. No website scraping or LLM extraction is proposed.

Portkey's [models repository](https://github.com/Portkey-AI/models) is a viable
structured alternative. Its public Anthropic JSON already contains Sonnet
5.5's input/output/read/five-minute-write/one-hour-write rates. Prices use
cents per token, so multiply by 10,000 to obtain USD per million. Its general
model configuration is separate from its pricing catalog. The inspected
Gemini 3.8 Flash pricing record contains a cache-read rate but no explicit
cache-write or storage field.

Two recent additions give limited evidence about relative freshness:

| Model | OpenRouter catalog `created`, UTC | Portkey addition commit, UTC |
| --- | --- | --- |
| Sonnet 5.5 | September 28, 18:04:46 | [September 28, 20:15:58](https://github.com/Portkey-AI/models/commit/f81ffd1f886a8d01815ada82de112c95358000fa) |
| Opus 5.5 | September 22, 16:32:12 | [September 22, 17:30:35](https://github.com/Portkey-AI/models/commit/9490598e5ee9ce56388a6145aa4c5a794d4ea3eb) |

These compare API creation metadata with Git commit timestamps, not continuous
observations of first public availability. They support OpenRouter as a
reasonable choice for launch freshness, but establish neither a general
latency bound nor a zero-delay guarantee. Both sources had the sampled models
when checked. OpenRouter says it publishes model information as it confirms
it in its [Models API documentation](https://openrouter.ai/docs/guides/overview/models).

The proposed collector would discover models through `GET /api/v1/models` and
read complete offers through `GET /api/v1/models/{author}/{slug}/endpoints`.
Retain a specific provider endpoint's prices together. Prefer the originating
lab endpoint when available, and label other hosting providers explicitly.
The generic catalog's price is the top provider's price, not a universal rate.
Even an originating-lab endpoint is an offer through OpenRouter and should be
labeled accordingly. Do not claim that every lab has an OpenRouter contract
or that every model is covered.

For a launch-focused page, propose polling discovery every 15 minutes, fetching
new offers immediately, and refreshing existing offers on a bounded schedule
even when the top-level catalog has not changed. Honor upstream caching and
rate limits. Persist validated snapshots and serve those to readers. This is
a proposed cadence, not a scheduler change. Publication/deployment time and
the arrival of independent benchmark scores add their own latency; an
unscored release can appear as pending but cannot enter the intelligence
frontier yet.

Portkey can remain an investigation or audit source without automatic fallback
in the initial implementation. Keeping one live pricing source avoids silently
mixing offers and billing conventions. If OpenRouter omits a model or price
dimension, retain unknown status; if a fetch fails, retain the last-good offer
with its timestamp. The unresolved Gemini write semantics below still require
explicit handling, not an inferred number or a runtime web search.

Sonnet 5.5's apparent pricing error comes from what the UI calls "Price /1M."
The production artifact correctly stores $2 for input and $10 for output, but
displays a $4 blended rate. That blend assumes three input tokens per output
token and no caching. The main list and detail table omit that explanation;
the feed teaser keeps "blended" only in a tooltip. A reader expecting the
advertised input price therefore sees an unexplained doubling.

The collector combines Artificial Analysis prices and benchmark scores, Arena
preference scores, first-party announcement identities, and DeepSWE task
measurements. It writes a committed snapshot, which the static renderer turns
into JSON payloads and model detail pages. No request-time API is needed.
The September 29 production snapshot contains 200 reasoning variants
representing 127 models. None has cache pricing.

A dedicated `/models` page already exists, but it is a ranked list. Its optional
frontier filter uses intelligence or coding index against blended token price.
Charts appear only on individual model pages and compare DeepSWE pass@1 against
measured task cost. Sonnet 5.5 has no DeepSWE result, so its page has no graph
despite having an intelligence score. The detail page also contradicts itself:
it reports AA frontier membership, then says no frontier claim is made for AA
scores. The configuration restored those frontiers without updating the older
prose and chart policy.

The current frontier calculation matches all 200 published rows. Its limits
concern the comparison inputs: selection caps variants before frontier
calculation, reasoning configurations get collapsed, and prices lack provider
identity, verification timestamps, and cache conditions. An unavailable source
can also freeze the entire refresh, including prices, while the command exits
successfully.

Production evidence came from the live [model list](https://www.llm-digest.com/models),
[Sonnet detail page](https://www.llm-digest.com/models/claude-sonnet-5-5), and
[served catalog](https://www.llm-digest.com/models-data.json), generated at
`2026-09-29T08:33:48.826927+00:00`. The checkout's September 24 snapshot predates
Sonnet 5.5 and must not be mistaken for current production.

| Available measurements in that production snapshot | Variant rows | Distinct models |
| --- | ---: | ---: |
| Entire catalog | 200 | 127 |
| Input, output, and blended prices | 142 | 79 |
| Intelligence score and price together | 142 | 79 |
| Coding index and price together | 101 | 60 |
| DeepSWE score and measured task cost together | 48 | 23 |
| Cache rates | 0 | 0 |

Sonnet 5.5 has five effort variants. Its max-effort intelligence score is 56.0,
which qualifies for the current intelligence frontier at $4 blended. Its AA
coding index, Arena scores, and DeepSWE measurements are absent. All published
blends agree with `(3 * input + output) / 4` within $0.005. Recomputing frontier
metadata in memory with the current repository code reproduced all 200 rows.
These checks establish internal consistency, not independent price accuracy.

The following Sonnet rates were independently verified against
[Anthropic's pricing table](https://platform.claude.com/docs/en/about-claude/pricing).
They are USD per million tokens for the standard, global Claude API.

| Billing category | Sonnet 5.5 rate |
| --- | ---: |
| Uncached input | $2.00 |
| Output | $10.00 |
| Cache read | $0.20 |
| Cache write, 5-minute retention | $2.50 |
| Cache write, 1-hour retention | $4.00 |

Cache-write rates replace the ordinary input rate for those tokens; they are
not added to it. Rates must be stored by model rather than inferred from one
universal discount: Anthropic lists Opus 5.5 cache reads at $0.20 on $4 input,
and Fable 5.1 reads at $0.25 on $10 input. The table's model-specific values
should take precedence over a generic multiplier.

The billing provider's rate card is the authority for investigating a disputed
rate. This is distinct from selecting a structured source for automated
collection. The follow-up recommendation above selects OpenRouter for that
role; none of the inspected catalogs provides a complete, uniform
direct-provider billing model for every tracked model.

| Source | Verified access and useful fields | Recommended use and limitation |
| --- | --- | --- |
| Provider pricing documentation | Anthropic explicitly lists both cache-write durations; OpenAI lists cached input and writes; Google separates caching and storage. | Authority for the selected provider, tier, region, and cache mode. Requires provider-specific extraction and verification. |
| [OpenRouter models API](https://openrouter.ai/docs/api/api-reference/models/list-all-models-and-their-properties) and [endpoint API](https://openrouter.ai/docs/api/api-reference/endpoints/list-all-endpoints-for-a-model) | Public requests worked without a key. Actual Sonnet payload includes `input_cache_read`, `input_cache_write`, and `input_cache_write_1h`, in USD per token. | Strong candidate for automated OpenRouter offer data and cross-checking. Pin the endpoint; a catalog price is not automatically the lab's direct rate. |
| [Vercel AI Gateway models API](https://vercel.com/docs/ai-gateway/models-and-providers) | Public `/v1/models` request worked. Actual payload includes input/output, cache read/write, and some context, region, and service-tier prices. | Useful second commercial source. The inspected Sonnet row has no separate one-hour write field; Gemini has no cache-write field. Missing fields do not mean zero. |
| [Models.dev source repository](https://github.com/anomalyco/models.dev) | Provider TOMLs contain `cost.input`, `output`, `cache_read`, and `cache_write`, in USD per million. Sonnet's direct Anthropic record agrees with the official rates. | Useful community-maintained discovery and cross-check source with version history. Its public JSON request returned HTTP 403 here; GitHub source worked. The inspected Sonnet record does not encode a one-hour write rate. |
| [Artificial Analysis free API](https://artificialanalysis.ai/api-reference) | Existing integration supplies intelligence and coding indices. Documented pricing includes input, output, and a 3:1 blend. | Keep for independent evaluation scores. Its documented pricing example does not cover cache reads, writes, or storage. Retain required attribution. |

The public OpenRouter catalog returned 460 rows, of which 296 included a
cache-read field and 92 included a cache-write field. Those are catalog-wide
counts, not proven matches to our 127 models. Vercel returned 390 rows. Both
returned Sonnet's $2/$10/$0.20/$2.50 rates, and OpenRouter additionally returned
$4 for one-hour writes. Responses were inspected as data; no inference calls
or paid API operations were made.

There are material differences that a flat pair of cache columns cannot fully
describe:

- [OpenAI's current caching guide](https://developers.openai.com/api/docs/guides/prompt-caching)
  distinguishes GPT-5.6 and later from earlier models. Newer models charge
  1.25 times input for cache writes and 0.1 times input for reads; older models
  have no additional write charge. The newer write rate is a replacement
  category, not an additive fee. The [pricing page](https://developers.openai.com/api/docs/pricing)
  also distinguishes context tiers and service tiers. A provider-wide
  "OpenAI writes are free" rule would be wrong.
- [Google's pricing table](https://ai.google.dev/gemini-api/docs/pricing)
  includes storage in USD per million tokens per hour. Its
  [Interactions API caching](https://ai.google.dev/gemini-api/docs/caching)
  is implicit; [explicit caching](https://ai.google.dev/gemini-api/docs/generate-content/caching)
  has separate storage-duration accounting in the generateContent API.
  A storage rate cannot be relabeled as a per-token write rate without stating
  the duration and billing calculation.
- The live OpenRouter Gemini 3.8 Flash catalog exposed
  `input_cache_write=0.0000000416666666666667` dollars per token. Its
  [caching guide](https://openrouter.ai/docs/guides/best-practices/prompt-caching)
  describes input price plus five minutes of storage, whereas that numeric
  value corresponds to storage alone at $0.50 per million per hour. This is
  an unresolved semantic discrepancy, not a safe replacement write rate.
  Endpoint responses also distinguish discounted offers. Do not automatically
  normalize or apply another discount without validating its meaning.
- [DeepSeek's direct pricing](https://api-docs.deepseek.com/quick_start/pricing/)
  distinguishes hit/miss input and peak/off-peak schedules. The current Flash
  alias maps to V4.1 Flash; old accepted aliases can now serve a different
  model. Preserve model-version and offer identity, not just a normalized name.
- [Grok's billing guide](https://docs.x.ai/developers/advanced-api-usage/prompt-caching/usage-and-pricing)
  separates cached input, ordinary input, and output. Reasoning is billed as
  output, and the context threshold includes cached tokens. Confirm the exact
  model's rate card rather than deriving cache discounts for every Grok model.

The pricing record should therefore identify the model version, serving
provider and endpoint, region, currency, service tier, prompt-length band,
cache mode and retention, effective dates, source URL, fetched time, and
verified time. Store input/output/read rates, duration-specific writes, and
storage where applicable. Explicitly distinguish a total write-token rate
from an additional write surcharge. Unknown, unsupported, included in ordinary
input, and zero additional charge must remain different states.

For collection, use one OpenRouter adapter and exact model/offer mappings
without fuzzy cross-provider price joins. Validate units and conditions before
publishing rates, record conflicts, and preserve last-good prices with visible
age if a source fails. Refresh pricing independently so a DeepSWE parsing
failure cannot freeze it. The current six-hour cadence is a separate source
of launch delay; the follow-up above proposes a faster discovery cycle.
Do not promise complete cache coverage until an audit has matched all 127
model identities to available offers; some may remain unknown or no longer
have a direct-provider offer.

For the future comparison page, the recommended starting point is a linked
`/models/compare` page while retaining the finishable model list. Put intelligence
on the vertical axis and a clearly named cost basis on the horizontal axis.
Offer individual input/output/cache rates and an estimated workload mode;
make the estimate the useful comparison for repeated-context coding sessions.
Use log cost, visible axis values, labeled frontier models, keyboard/touch
selection, and an accessible table. A route must precede `/models/:slug`.
The same static catalog can serve it without another serverless function.

A price frontier means that no other included configuration is both no more
expensive and at least as capable, with a strict improvement in one dimension.
It is conditional on the selected metric, workload, offers, and catalog. It
does not establish a universally best model or the cost of completing a task.

For providers whose normalized write price is the total charge for that token
category, a workload calculation can use:

```text
estimated USD =
  (ordinary_input * input_rate
   + cache_read * read_rate
   + cache_write_5m * write_5m_rate
   + cache_write_1h * write_1h_rate
   + billable_output * output_rate) / 1,000,000
  + storage_USD
```

Each input token belongs to exactly one category in this formula. Other
providers need their own normalization, including ordinary processing charges
where applicable; raw usage fields must not be summed blindly. Billable output
must include reasoning tokens according to the selected provider's accounting.
Storage uses retained tokens and elapsed time, not the number of reads.

The UI must disclose total input and output volume, token-weighted cache-hit
share, the share written to cache, and retention or storage duration. A 90%
hit preset can illustrate a warm coding session, but is not a measured claim
about most users. For example, one million Sonnet input tokens consisting of
900,000 reads and 100,000 five-minute writes cost `$0.18 + $0.25 = $0.43`,
before output. Using one-hour writes makes that `$0.58`. This is already very
different from both the $2 uncached input rate and the site's $4 blend.

Compute the frontier again whenever the scenario or filters change. Keep each
score paired with its evaluated effort/configuration, and show benchmark
version/date when available. Do not silently substitute Arena Elo for an
intelligence index or pair one variant's score with another variant's cost.
Unknown rates exclude a point from that cost comparison, with the omitted
count explained. Genuine free offers need explicit handling on a logarithmic
axis. The current 200-variant cap should not silently define "best available."

Retain measured DeepSWE task cost as a separate view. It includes actual model
token consumption and task behavior that a common-token estimate cannot
capture. Existing stored DeepSWE data does not include enough input/cache
usage to reprice its historical runs under an arbitrary new cache scenario.

The main implementation locations and limitations found during inspection:

| Location | Current behavior or issue |
| --- | --- |
| `pipeline/collect_models.py:427,1559` | Extracts AA rates and preserves or calculates the blend. Some fallback aliases name per-token prices without converting units; current live first-choice fields are consistent. |
| `pipeline/collect_models.py:1794,1939` | Computes frontier membership and preserves qualifying variant score/cost. |
| `pipeline/collect_models.py:1976` | Caps variant rows before computing frontiers. |
| `pipeline/collect_models.py:2302,2462` | Whole-snapshot source-regression guard; missing source blocks all updates with exit zero. Partial field/coverage loss is not similarly guarded. |
| `config/models.yaml:307` | Configures intelligence/price, coding/price, and measured DeepSWE frontiers. |
| `web/models.html:383,518` | Chooses intelligence-first representative even when sorting by coding; always displays intelligence. Price label omits blend assumptions. |
| `web/index.html:4404,4523` | Feed teaser removes "blended" from visible price text. |
| `pipeline/render_static_pages.py:4591,4914` | Frontier section and AA explanatory prose contradict each other. |
| `pipeline/render_static_pages.py:4626,4795` | Detail graph requires DeepSWE score and cost. It has no numeric tick labels, visible point names, or point links; mobile uses horizontal scrolling. |
| `pipeline/render_static_pages.py:4973,5183` | Renders blended variant prices and writes public static JSON. |
| `tests/test_models_surface.py:210,714` | Tests enforce no chart on the root list and no additional models API function. |
| `tests/test_model_detail_pages.py:191` | Test preserves the obsolete no-AA-frontier statement. |
| `.github/workflows/models-refresh.yml:11` | Six-hour GitHub schedule at 02:20/08:20/14:20/20:20 UTC. |

Before implementation, settle the default offer policy and scenario. The
follow-up recommends standard, global text offers through OpenRouter, preferring
the originating lab where available and identifying the selected provider.
Show all component rates and let the user change the workload. Do not silently
choose the cheapest provider independently for each rate.

Implementation should proceed through independently verifiable changes:
correct the price labels and conflicting frontier prose; introduce validated
offer/rate data and freshness handling; then add the comparison page. Update
the concept/spec, stale collector comments, generated schema through its
supported process, and assertions that currently encode the old chart policy.
Do not hand-edit generated model JSON or HTML. No such implementation work was
performed during this investigation.
