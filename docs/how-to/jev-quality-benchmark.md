# Test Jev as a feed quality judge

This runbook covers the small benchmark in
`data/quality/benchmark/`. The goal is to decide whether Jev is a useful
coarse quality gate before it touches the production feed.

## 1. Review the labels first

Open `data/quality/benchmark/labels.md` and read the 50 rows. The labels are
assistant-authored and provisional. Correct any row where the expected label
is wrong, especially:

- a corporate announcement that actually contains a useful engineering change
- a search result that is a genuine scoop rather than SEO
- a practitioner post that is off-mission despite the source
- a research paper that is too niche for the platform-engineering lens

Edit `data/quality/benchmark/items.json` directly, then regenerate the table:

```bash
python3 scripts/build_quality_benchmark.py
```

If you change the excerpt or add an item, keep the `id`, `slice`, `expected`,
and `expected_label` fields. The benchmark runner uses those fields.

## 2. Validate the harness without Jev

```bash
python3 pipeline/quality_benchmark.py run \
  --provider fixture \
  --scores data/quality/benchmark/fixture_scores.json
```

This proves the report, metrics, and review packet work. The fixture is
synthetic; the report labels it as such. Run the deterministic baseline too:

```bash
python3 pipeline/quality_benchmark.py run --provider heuristic
```

The heuristic is a source/title rule, not a judge. It exists to give Jev a
bar to beat on the same labels. Because the labels are assistant-authored,
the heuristic may share some of the label author's biases; treat it as a
sanity baseline, not an independent gold standard.

## 3. Configure the provider

The recommended path is OpenRouter's System One API. OpenRouter exposes Jev as
a typed decision model, not a chat model:

```text
POST https://openrouter.ai/api/v1/systemone
{
  "model": "jev-1.14",
  "state": "Title: ...\nSource: ...\nExcerpt: ...",
  "questions": {
    "keep":              { "type": "noul", "instructions": "Does this item belong in the default Brief?" },
    "platform_relevant": { "type": "noul", "instructions": "Is it platform/agent engineering rather than a domain application?" },
    "release_lane":      { "type": "noul", "instructions": "Is it a routine release note or bare version bump?" },
    "corporate_marketing": { "type": "noul", "instructions": "Is it a marketing or corporate announcement without a concrete change?" }
  }
}
```

Each `noul` question returns `answers.<id>.noul`. The benchmark uses `keep` as
the primary score and the other three as hard gates: a high `release_lane` or
`corporate_marketing`, or a low `platform_relevant`, clamps the item to a low
score. This hybrid beat both the single-question prompt and the heuristic
baseline in the 2026-10-24 run.

Export the key:

```bash
export OPENROUTER_API_KEY="..."
# optional overrides
export OPENROUTER_SYSTEMONE_ENDPOINT="https://openrouter.ai/api/v1/systemone"
export OPENROUTER_JEV_MODEL="jev-1.14"
```

`config/judge.yaml` already contains the hybrid setup:

```yaml
provider: openrouter
openrouter:
  endpoint: https://openrouter.ai/api/v1/systemone
  model: jev-1.14
  api_key_env: OPENROUTER_API_KEY
  score_mode: hybrid
  use_holistic_keep: true
  questions:
    platform_relevant: { type: noul, instructions: "..." }
    release_lane:      { type: noul, instructions: "..." }
    corporate_marketing: { type: noul, instructions: "..." }
  hybrid:
    primary: keep
    drop_if_above:
      release_lane: 0.6
      corporate_marketing: 0.7
    drop_if_below:
      platform_relevant: 0.35
    gate_score: 0.1
```

Use `jev-1.13` if you want the exact version Hamel Husain tested; `jev-1.14`
is the current release. The bare ID is mapped to `typesafe/jev-1.14` by
OpenRouter. Jev's OpenRouter listing shows a 262,144-token context and
$0.042 per million input tokens, so the benchmark's 2,500-character excerpts
are far below the limit.

If you have direct TypeSafe Decisions API access, fill the top-level
`endpoint` and `JEV_API_KEY`, then use `--provider jev`. That path sends the
structured `version` / `question_id` / `type` / `instructions` / `criteria`
request from Hamel's example.

Inspect the exact requests before spending on a run:

```bash
python3 pipeline/quality_benchmark.py run --provider openrouter --request-only
```

This writes one JSON payload per item to `runs/openrouter-<timestamp>/requests/`.
Send one manually to the API and check the response shape.

## 4. Run Jev

```bash
python3 pipeline/quality_benchmark.py run --provider openrouter
```

The runner caches every response under `data/quality/cache/openrouter/` by
payload hash, so reruns and threshold changes do not make new API calls. It
prints:

```text
BENCHMARK_OK provider=openrouter items=50 auc=... precision=... recall=... f1=...
threshold=... brier=... ece10=... false_pos=... false_neg=... report=...
```

## 5. Read the report

Open `data/quality/benchmark/runs/<provider>-<timestamp>/report.md`.

- **AUC** measures ranking quality, not calibration.
- **Brier** and **ECE(10)** measure probability calibration. A judge can
  rank well and still be badly calibrated.
- **At 0.50** is the default threshold. Do not ship on it.
- **Tuned** is the threshold chosen from the sweep. The runner prefers a
  threshold that clears 80% precision and 80% recall when one exists.
- **By slice** shows where the judge fails. A good overall F1 can hide a
  collapsed `search_seo` or `off_topic_domain` slice.
- **Review** points to `review.md`.

For the feed, precision matters more than recall. A junk card costs a story
slot; a missed good post costs one item. A reasonable first policy is a
high-precision drop threshold plus a gray band for a generative judge.

## 6. Adjudicate the review packet

Open `review.md`. It lists:

- false positives: Jev kept, the label says drop
- false negatives: Jev dropped, the label says keep
- ambiguous scores in the 0.35-0.65 band

For each case, mark one:

- `label_error`: the benchmark label is wrong. Fix `items.json` and rerun.
- `judge_error`: the label is right and Jev is wrong. Record the failure mode.
- `ambiguous`: the item is genuinely borderline; leave it for the owner.

The packet is deliberately compact and includes the title, source, score,
expected label, rationale, URL, and a 700-character excerpt. It is designed
to be pasted into a chat with the assistant for a second opinion.

## 7. Decide

The Jev 1.14 run is recorded in
`docs/status/jev-quality-benchmark-2026-10-24.md`. The hybrid four-question
gate (`keep` plus `platform_relevant`/`release_lane`/`corporate_marketing`)
scores AUC 0.969, F1 0.927 at threshold 0.25, Brier 0.095, ECE 0.114, 50
requests for $0.0027. It beat both the single-question prompt and the
heuristic baseline, but search title-only items remain weak. Treat that as the
starting point, not a production verdict.

Jev is worth wiring into the pipeline only if all of these hold:

- it beats the heuristic baseline on the same labels;
- it clears the precision and recall floors at a usable threshold;
- it holds up on the hard slices (`first_party_marketing`, `search_seo`,
  `off_topic_domain`);
- Brier and ECE are acceptable, or a calibration step fixes them;
- the false positives and false negatives in the review packet are mostly
  judge errors we can tolerate, not systematic failures.

If it passes, the next step is shadow mode in the pipeline: score candidates,
log the verdict, and do not change ranking until a larger reviewed sample
confirms the threshold. If it fails, the harness still gives us a labeled set
for a different decision model or a generative judge.

## Troubleshooting

- `openrouter_not_configured`: export `OPENROUTER_API_KEY`.
- `jev_not_configured`: for the direct provider, set `endpoint` and export the
  key named by `api_key_env`.
- `No noul probability in System One response`: inspect the cached raw
  response under `data/quality/cache/openrouter/`; the expected shape is
  `answers.<question_id>.noul`.
- `openrouter_http_429` / `jev_http_429`: the runner retries with backoff.
  Reduce concurrency or wait.
- A short excerpt: search results and some first-party feeds only expose a
  teaser. The benchmark keeps the title and teaser rather than inventing
  body text. This is a fair representation of what the live gate would see.
