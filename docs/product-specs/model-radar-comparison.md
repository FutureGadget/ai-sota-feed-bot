# Model Radar prices and comparison

The Radar helps engineers compare model capability and token spend. `/models`
keeps the ranked list; `/models/compare` provides the interactive Pareto chart.
Every model detail page has a static token-price table.

## Sources and refresh

OpenRouter is the sole automated source of served token prices and provider
metadata. Artificial Analysis supplies capability scores; LMArena supplies
community preference; DeepSWE supplies measured coding-task costs. Provider
pricing pages and Portkey can be used for manual audits, never automatic
field-by-field fallback. See the [source investigation](../ideas/model-radar-cache-pricing-investigation.md).

`pipeline/model_pricing.py` fetches the public models JSON for discovery and
provider endpoint JSON for prices. It writes `data/models/pricing.json` atomically.
The `model-prices-refresh.yml` workflow requests a refresh every 15 minutes,
independently of the six-hour benchmark workflow. GitHub scheduling, upstream
publication, and deployment add latency; this is not a freshness SLA.

Each run checks the catalog and refreshes up to 32 endpoint sets with four
concurrent requests. New or changed catalog prices and failed refreshes take
priority; unchanged endpoints become due after four hours. The initial seed can
use `python pipeline/model_pricing.py --max-endpoints 500`. Collection works without a key in the verified live API. An optional
`OPENROUTER_API_KEY` is supported because the endpoint reference documents
authentication. No LLM or HTML pricing parser is involved.

A catalog failure or severe coverage regression retains the last successful
catalog. An endpoint failure retains its entire last successful offer set and
original check time. Successful endpoints advance independently. Prices older
than 24 hours remain visible with their check time but are excluded from
estimates. Benchmark collection failures cannot overwrite the separate pricing
snapshot. A missing pricing snapshot yields unknown prices, never AA fallback.

## Data contract

`pricing.json` version 1 stores `catalog_checked_at`, `attempted_at`, `error`,
and a map of OpenRouter model IDs to records. A model record contains identity,
OpenRouter catalog-added time (not release time), catalog and successfully
refreshed price fingerprints, endpoint check time, source URL, refresh error,
and complete provider offers. Removed catalog entries disappear on a successful
catalog fetch. Routing pseudo-models and colon-suffixed service variants are
excluded.

Each offer stores provider name, endpoint tag, context and output limits,
supported parameters, check time, and rates in **USD per million tokens**:
`input`, `output`, `cache_read`, `cache_write`, `cache_write_1h`. The API's USD
per-token values are multiplied by 1,000,000. Zero is a real rate; null means
unknown. Published discounts are not applied again. `tiers` retains prompt-length
overrides as complete rate sets. `request_usd` stays in USD per request.

The selected offer prefers the originating provider, then the cheapest input
rate among standard endpoints, breaking ties by output rate and endpoint tag.
The tag identifies quantization where published. Regional, flex, priority and
unrecognized endpoint qualifiers are excluded. All rates belong to one offer.
This compares the disclosed OpenRouter serving offer, not a claim that all
providers reproduce the benchmark configuration exactly.

`render_static_pages.load_models_artifact()` joins the pricing snapshot with the
benchmark artifact at build time. Matching requires an exact normalized model
name within the same organization, with reviewed alias exceptions in
`config/models.yaml`. Ambiguous matches remain unknown. Recently added catalog
models without scores are included as pending; no release date or score is
inferred. Existing score/effort pairs remain intact. The merged artifact feeds
`web/models-data.json`, the smaller feed teaser, and static detail pages. The
legacy input/output/blended fields in the raw benchmark snapshot are replaced
before serving; token frontier annotations are recomputed from OpenRouter rates.

## Cache accounting

Cache reads and writes are disjoint, token-weighted fractions of total input.
The remainder is ordinary uncached input. The user chooses total input and
output volume, cache fractions, write duration, and prompt tokens per request.
Output includes billed reasoning tokens. The context-size field selects a rate
tier; it is not the aggregate workload size.

Cost in USD is:

```
(input_tokens / 1e6) * ((1 - read_share - write_share) * input_rate
                     + read_share * cache_read_rate
                     + write_share * cache_write_rate)
+ (output_tokens / 1e6) * output_rate
```

Anthropic and OpenAI's published write rates have a verified replacement basis.
They replace the ordinary input charge, rather than adding to it. The default
write duration is 5 minutes for Anthropic and 30 minutes for OpenAI models with
an explicit write rate. One-hour writes use the separate published field.
No write multiplier, included-write price, or storage fee is inferred from a
missing field. Other providers' write semantics remain unverified until audited.
Google's write field has unresolved storage-time semantics and cannot be used
as a total write rate. It displays as **Unverified**, with raw data retained.

A missing rate only excludes a model when the workload uses that token class.
Other exclusions are stale prices, unknown/exceeded context limits, and
additional per-request fees that cannot be estimated from token volume alone.
The table retains excluded models and explains the reason.

Example: Sonnet 5.5 input/output/read/5m-write/1h-write rates are
$2 / $10 / $0.20 / $2.50 / $4 per million. For 1M input, 250k output,
90% reads and 10% writes, estimated spend is $2.93 with short writes or $3.08
with one-hour writes. An uncached workload costs $4.50.

## Presentation and frontier

The ranked list and feed teaser label input rates explicitly. The old $4 Sonnet
value was a 3:1 input/output blend; it is retained only where explicitly labeled
as a blended rate. Each detail page shows the five separate rates, provider,
check time, and source link. Existing DeepSWE charts remain separate from token
estimates, and AA score sections link to the new comparison.

The comparison defaults to 1M input, 250k output, 90% cache reads, 10% writes,
and a 32k prompt. It supports AA intelligence and coding indices. One point per
model uses the highest-scoring measured effort for the chosen metric, disclosed
on selection and in the table. A point is dominated when another costs no more
and scores no lower, with at least one strict improvement. Exact ties survive.
The frontier is recomputed for every valid workload change. It is optimal only
among comparable, tracked models for those assumptions, not a task-cost ranking.

The responsive chart labels axes and frontier models. The compressed cost axis
uses log(1 + cost), retaining actual zero-cost points. Points support keyboard
selection, and a searchable table exposes all values without relying on hover.
Read/write shares above 100% produce an explicit error and clear stale results.
Prices and estimates retain sub-cent precision. The page works through static
JSON and adds no serverless function.

## Verification

- `python -m unittest discover -s tests -p 'test_model*.py'`
- `python -m pytest tests/test_collect_models.py -q`
- `node tests/model_comparison.mjs`
- `python scripts/check_bundle_size.py`
- Open the list, Sonnet detail, and comparison with live-generated data at
  desktop and 390px widths. Exercise cache duration, invalid shares, metric
  changes, long-context tiers, search, keyboard points and dark mode.
