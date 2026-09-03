# Execution Plan: OpenReview accepted-paper source and ICLR 2026 collection

## Status

In progress 2026-09-04. The reusable collector and ICLR source configuration
are implemented; historical collection remains out of scope for this phase.

## Objective

Give platform and agent engineers a reliable way to discover high-signal ICLR
research without turning the finishable feed into a conference-paper dump.

The work has two intentionally separate outcomes:

1. An ongoing, reusable OpenReview collector that makes newly accepted ICLR
   papers eligible for the regular feed.
2. A one-time, dated ICLR 2026 editorial collection that gives readers a
   durable place to discover older standouts such as GEPA without mislabeling
   them as fresh news.

## Product and architecture decisions

### Accepted papers only

The collector reads only papers whose public OpenReview decision is an
acceptance. It must not ingest anonymous submissions, reviews, rebuttals,
withdrawals, or rejected papers.

### Generic collector, ICLR-first configuration

Add one `openreview_venue` source type to `collectors/collect.py`. Its
configuration supplies a venue ID and accepted-only policy, so future venues
such as ICML and NeurIPS require configuration rather than another collector.

The first configured source is:

```yaml
- name: openreview_iclr_accepted
  type: openreview_venue
  venue_id: ICLR.cc/2026/Conference
  accepted_only: true
  max_results: 100
```

The implementation must use the public OpenReview API v2. It must paginate
responses and preserve a useful health-stat URL such as
`openreview://ICLR.cc/2026/Conference`.

### Decision timestamp controls freshness

Every emitted paper uses the acceptance decision's public timestamp as
`published`. It must never use the original submission timestamp or the
collector's current time. If a public decision timestamp cannot be recovered,
the paper is skipped and the collector reports why.

This preserves the feed's freshness policy and prevents a previously accepted
conference batch from becoming newly fresh on every polling run.

### Existing research slot remains the reader gate

Map the source to `research_watch` in both `config/ranking.yaml` and
`config/presets/balanced.yaml`. Start with `max_per_source: 1` and a cautious
source bias near the other research feeds. Do not create a dedicated ICLR
slot, change the global research cap, or reserve feed space for conference
papers.

The normal title-and-abstract relevance score determines which accepted paper
can win that one position. This is more durable than a GEPA-specific keyword
rule.

### A historical collection is distinct from the live feed

ICLR 2026 decisions are outside the live feed freshness window. The one-time
backfill is therefore a clearly dated collection at
`/research/iclr-2026`, backed by a curated data artifact. It is not inserted
into `data/processed/latest.json`, given an artificial publication date, or
used to alter recurring ranking results.

The collection has a small, editorially selected set of directly relevant
papers. Each card links to OpenReview and, when available, arXiv or official
code; its short explanation names the operational lesson without overstating
the paper's evidence.

## Non-goals

- Ingest ICLR submissions before final decisions.
- Claim that acceptance alone proves practical relevance or reproducibility.
- Backdate, redate, or otherwise force historical papers into the live feed.
- Re-enable LLM ranking in the hourly pipeline.
- Build a general conference browser, search product, or personalized research
  recommendation feature.

## Dependency graph

```text
OpenReview API contract + decision-time extraction
    -> collector normalization and unit tests
        -> ICLR source configuration
            -> research_watch mapping and ranking fixture
                -> source exposure validation

Accepted-paper candidate export
    -> editorial selection and evidence review
        -> validated ICLR 2026 collection artifact
            -> static /research/iclr-2026 rendering
                -> visual and link verification
```

## Task list

### Phase 1: Source contract and collection

#### Task 1: Establish the OpenReview API contract with fixtures

**Description:** Confirm the public API v2 response shape for ICLR 2026 and
write compact recorded fixtures for accepted, rejected, withdrawn, paginated,
and malformed records. Define the normalized item contract before adding the
source to production configuration.

**Acceptance criteria:**

- [x] The chosen query returns public accepted ICLR papers without a user
  credential, or the plan has a documented safe fallback.
- [x] The fixture includes title, abstract, forum ID, decision, and decision
  timestamp in the actual response shape.
- [x] Rejected, withdrawn, anonymous, and timestamp-less records are excluded
  with a testable reason.

**Verification:**

- [ ] A read-only live API probe succeeds against the official API.
- [x] Unit tests load fixtures without network access.

The live probe returned OpenReview's `ChallengeRequiredError` on 2026-09-04.
The safe fallback is the official API v2 contract plus recorded fixtures; no
credential or challenge bypass is used.

**Dependencies:** None.

**Files likely touched:**

- `collectors/collect.py`
- `tests/fixtures/openreview/` (new)
- `tests/test_openreview_collector.py` (new)

**Estimated scope:** Small.

#### Task 2: Implement the generic accepted-venue collector

**Description:** Add `collect_from_openreview_venue()` using the existing
standard-library HTTP approach. It paginates safely, normalizes accepted notes,
and returns a normal collector entry with a stable forum URL and decision-time
publication date.

**Acceptance criteria:**

- [x] The collector supports an arbitrary configured venue ID and `max_results`.
- [x] It uses API v2 pagination and has a bounded request timeout.
- [x] API errors flow through existing source-health and circuit-breaker paths.
- [ ] A duplicate arXiv paper is collapsed by the existing title/URL dedupe
  before ranking.

**Verification:**

- [x] `pytest -q tests/test_openreview_collector.py` passes.
- [ ] Existing collector tests pass.
- [ ] A local collection run records an intelligible source health result.

**Dependencies:** Task 1.

**Files likely touched:**

- `collectors/collect.py`
- `tests/test_openreview_collector.py` (new)

**Estimated scope:** Medium.

### Checkpoint: Collector foundation

- [x] The OpenReview fixture tests pass.
- [ ] The live API accepts unattended requests from the production runtime.
- [x] Source configuration was enabled only after the collector produced
  correct decision-time records.

### Phase 2: Reader exposure

#### Task 3: Configure and tune the ICLR source

**Description:** Add `openreview_iclr_accepted` to the source list and map it
to the existing research slot in both the active override and the balanced
preset. Use an initial source bias that permits exceptional papers to compete
without displacing the regular research mix by default.

**Acceptance criteria:**

- [x] The source is mapped in both ranking files and never falls into overflow.
- [x] It has no dedicated feed floor or reserved seat.
- [x] Its configured poll interval is appropriate for a low-frequency venue
  source and does not add needless API traffic.

**Verification:**

- [x] YAML parsing and ranking-config loading succeed.
- [x] `validate_source.py --source openreview_iclr_accepted --items
  tests/fixtures/openreview/exposure.json` reports the
  correct slot mapping.

**Dependencies:** Task 2.

**Files likely touched:**

- `config/sources.yaml`
- `config/ranking.yaml`
- `config/presets/balanced.yaml`
- `tests/test_ranking_*.py` as needed

**Estimated scope:** Small.

#### Task 4: Prove the full ranking path without falsifying freshness

**Description:** Run an end-to-end pipeline fixture containing a newly
accepted, relevant ICLR paper. It must pass collection, Tier 1 dedupe,
research-slot ranking, and final feed selection. Separately run the live ICLR
2026 source as a health check; its old papers are correctly expected to age
out of the current feed.

**Acceptance criteria:**

- [x] The fresh acceptance fixture produces `EXPOSED` through the source
  validator.
- [ ] A duplicate arXiv fixture appears only once in ranked output.
- [ ] Live ICLR 2026 records keep their authentic decision dates and do not
  surface merely because they were collected today.

**Verification:**

- [x] `python .agents/skills/add-source/scripts/validate_source.py --source openreview_iclr_accepted --items tests/fixtures/openreview/exposure.json` exits 0.
- [ ] Tier 1, ranking, and relevant collector tests pass.

**Dependencies:** Task 3.

**Files likely touched:**

- `tests/test_openreview_collector.py`
- `tests/test_ranking_*.py` as needed
- no committed runtime data

**Estimated scope:** Medium.

### Checkpoint: Ongoing source ready

- [ ] Fresh accepted papers can reach readers.
- [ ] Historical papers remain outside the live feed.
- [ ] The source passes the exposure gauntlet without increasing global caps.

### Phase 3: ICLR 2026 historical collection

#### Task 5: Define and validate the editorial collection artifact

**Description:** Add a small, durable schema for a dated research collection
and a deterministic validator. The ICLR 2026 artifact contains only selected
papers, source links, publication metadata, and evidence-grounded editorial
notes.

**Acceptance criteria:**

- [ ] Collection and paper slugs, URLs, and titles are unique and valid.
- [ ] Every card links to its OpenReview record and preserves the official
  acceptance year.
- [ ] Every editorial note is source-backed and contains no unsupported
  quantitative claim.
- [ ] The collection is explicitly labeled as ICLR 2026, not live news.

**Verification:**

- [ ] Validator accepts a complete fixture and rejects duplicate/missing links.
- [ ] Editorial review checks every card against its primary source.

**Dependencies:** Task 1.

**Files likely touched:**

- `data/research-collections/iclr-2026.json` (new, curated)
- `pipeline/build_research_collections.py` (new)
- `tests/test_research_collections.py` (new)

**Estimated scope:** Medium.

#### Task 6: Render the durable collection page

**Description:** Extend the static renderer and Vercel rewrites to serve the
validated ICLR collection at `/research/iclr-2026`. Reuse the site chrome,
semantic fallback links, metadata, and mobile layout conventions.

**Acceptance criteria:**

- [ ] The public URL renders title, date, context, paper links, and a clear
  distinction from the live feed.
- [ ] The page is included in the sitemap and has canonical/Open Graph metadata.
- [ ] No changes make historical papers appear as current feed entries.

**Verification:**

- [ ] Static renderer tests pass.
- [ ] Local browser review verifies desktop and mobile layout, links, console,
  and network responses.
- [ ] Vercel preview is checked before merge.

**Dependencies:** Task 5.

**Files likely touched:**

- `pipeline/render_static_pages.py`
- `vercel.json`
- `web/site-chrome.css` only if a small shared style addition is necessary
- `tests/test_research_collections.py`
- renderer/site tests as needed

**Estimated scope:** Medium.

### Phase 4: Documentation and release

#### Task 7: Record the operating policy and release separately

**Description:** Document the accepted-only policy, freshness rule, ICLR 2026
collection contract, and rollback procedure. Commit code/config/docs separately
from any generated static output, following repository data hygiene.

**Acceptance criteria:**

- [ ] The decision log includes rationale, impact, and rollback for the new
  source and historical collection.
- [ ] Product docs explain where live accepted papers and historical collections
  differ.
- [ ] The source can be removed by configuration and the collection page can be
  removed by deleting its explicit artifact and route registration.

**Verification:**

- [ ] Full targeted test suite passes.
- [ ] `git diff --check` passes.
- [ ] Preview and production deployment checks show no broken source links.

**Dependencies:** Tasks 4 and 6.

**Files likely touched:**

- `docs/design-docs/decision-log.md`
- `docs/product-specs/` relevant index/spec
- `docs/generated/db-schema.md` if the collection artifact is committed

**Estimated scope:** Small.

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| OpenReview response shape or unauthenticated access differs by venue | High | Prove the live API contract before enabling config; keep recorded fixtures and fail gracefully. |
| Bulk acceptance decisions crowd out the feed | Medium | Existing research cap, one per source, no reserved seat, and source bias stay in force. |
| Historic papers are made to look newly published | High | Use decision timestamps for live ingestion and a separate dated collection for backfill. |
| Duplicate arXiv and OpenReview entries | Medium | Assert the existing title/URL dedupe path in end-to-end tests. |
| Editorial notes overstate a paper's result | Medium | Primary-source review and validator rules prohibit unsupported numeric claims. |

## Approval checkpoint

Implementation begins only after this plan is approved. The first implementation
step is the read-only OpenReview API contract probe, not a production config
change.
