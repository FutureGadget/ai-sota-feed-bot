# How-To: Add Data Sources and Debug Filtering (v2)

This guide explains how to add new ingestion sources safely and how to debug where items are being dropped in the v2 ranking pipeline.

## 1) Add a new source

Edit: `config/sources.yaml`

Example (RSS):
```yaml
- name: example_source
  type: rss
  url: "https://example.com/feed.xml"
  weight: 1.0
```

Example (sitemap):
```yaml
- name: example_docs
  type: sitemap
  url: "https://example.com/sitemap.xml"
  include_prefixes:
    - "https://example.com/research/"
  weight: 1.1
```

Example (arXiv API):
```yaml
- name: arxiv_cs_ai
  type: arxiv_api
  category: cs.AI
  max_results: 40
  weight: 0.85
```

### Source naming conventions
- Use stable snake_case names.
- Source name is used in slot mapping (`config/ranking_v2.yaml`) and diagnostics.

---

## 2) Map source to a v2 slot

Edit: `config/ranking_v2.yaml` under `slots.*.sources`.

If a source is not mapped, it falls into `overflow` behavior.
Always map intentionally to avoid accidental ranking behavior.

Current slot families:
- `frontier_official`
- `agent_tooling_releases`
- `infra_runtime_releases`
- `vendor_general_updates`
- `practitioner_analysis`
- `community_signal`
- `research_watch`
- `overflow`

---

## 3) Run and validate ingestion

```bash
python collectors/collect.py
```

Check source health lines in logs:
- `sources_ok=...`
- `sources_error=...`

Inspect raw items:
```bash
python - <<'PY'
import json
from collections import Counter
items=json.load(open('data/raw/2026-02-15/items.json'))
print(Counter(x.get('source') for x in items).most_common(20))
PY
```

---

## 4) Debug filtering/ranking drops (v2)

### Pipeline checkpoints
1. **Raw ingest** (`data/raw/.../items.json`)
2. **Prefilter** (`prefilter_in -> prefilter_out` in `v2_stats`)
3. **Slot candidates/selection** (in `data/diagnostics/YYYY-MM-DD_v2.json`)
4. **Final output** (`data/processed/latest.json`)

### Key logs to read
- `v2_stats prefilter=A->B llm_used=X/Y slots=... slot_priority=... total=...`

Interpretation:
- `A->B`: candidate reduction before slot scoring
- `llm_used`: actual LLM calls consumed by v2 budget
- `slots=...`: selected count per slot
- `slot_priority=...`: dynamic slot rerank weights applied

### Diagnostics file
`data/diagnostics/YYYY-MM-DD_v2.json` includes:
- prefilter counts/reasons
- per-slot candidate/scored/selected counts
- budget usage

---

## 5) Common reasons items disappear

1. **Not ingested**
- source failing or parser mismatch.

2. **Prefiltered out**
- title regex exclude
- freshness window too short for that slot
- source health floor
- candidate pool cap reached (`candidate_pool_cap`)

3. **Slot competition**
- slot `max_items` too low
- `max_per_source` reached

4. **Top-band constraints**
- top-10 rules (e.g., research cap) can push items lower.

5. **Bias tuning**
- `source_bias`, `topical_bias`, and slot priority can demote/promote.

---

## 6) Fast debugging recipes

### A) Find unmapped sources
```bash
python - <<'PY'
import yaml
slots=yaml.safe_load(open('config/ranking_v2.yaml'))['slots']
sources=yaml.safe_load(open('config/sources.yaml'))['sources']
mapped={s for k,v in slots.items() for s in v.get('sources',[])}
all_names=[x['name'] for x in sources]
print([n for n in all_names if n not in mapped])
PY
```

### B) Check final presence by source family
```bash
python - <<'PY'
import json
from collections import Counter
items=json.load(open('data/processed/latest.json'))
print(Counter(x['source'] for x in items))
PY
```

### C) Force fresh v2 label behavior
```bash
rm -f data/llm/labels_v2.json
python pipeline/build_digest.py
```

---

## 7) Safe tuning order

When tuning source visibility:
1. slot mapping
2. slot `min_items` / `max_items`
3. `candidate_pool_cap`
4. `source_bias`
5. `topical_bias`
6. top-band constraints

Avoid changing many knobs at once unless running multiple validation passes.

---

## 8) Validation checklist before merging

- [ ] `python pipeline/build_digest.py` succeeds
- [ ] expected source appears in raw items
- [ ] expected slot candidate count looks sane
- [ ] final digest includes expected category presence
- [ ] `run_full.sh` reaches `FULL_RUN_OK`
- [ ] docs updated if new slot/category/source policy added
