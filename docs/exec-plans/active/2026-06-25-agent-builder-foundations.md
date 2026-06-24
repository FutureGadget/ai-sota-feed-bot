# Execution Plan — Agent Builder Foundations

## Status

First vertical slice implemented 2026-06-25: schema, compiler, API, static
pages, seed concept, curator skill, weekly routine config, docs, tests, and
generated pages.

## Problem

LLM Digest is becoming an agent-builder portal, but today its durable learning
surfaces are split between the obstacle/solution knowledge map (`/map`) and the
action-oriented Playbook (`/playbook`). There is no canonical place for stable
concept explanations such as "what makes a prompt reliable", "why RAG helps but
also fails", or "what an agent eval should measure".

If this is folded directly into the existing wiki, the content inherits an
obstacle/solution shape that is useful for diagnosis but too narrow for
scientific or empirical explanations. If it is treated as ordinary articles, it
loses the site's compounding-memory advantage.

## Outcome

Create a new top-level `/foundations` section for durable, evidence-backed
agent-builder learning pages. Foundations is the site's authority layer: the
place where serious builders can see that LLM Digest understands the mechanisms
behind agent work, not only the news cycle around it.

The section explains core LLM and agent-system concepts through builder
questions, grounded in papers, benchmarks, primary docs, and empirical field
reports. It assumes a strong software engineer with high mathematical capacity,
but explains the math in usable intuition before notation. It cross-links
heavily with `/map`, `/playbook`, storylines, and source stories, but keeps its
own authoring source of truth under `data/foundations/`.

## Success Criteria

- `/foundations` ships with an index and at least one high-quality concept page:
  "What makes a prompt reliable?"
- The first page starts from a builder consequence, explains the mechanism,
  gives optional math intuition, and ends with concrete application guidance.
- Every material claim on the initial page resolves to explicit evidence in the
  page front matter or body.
- Evidence is visibly tiered as theory/paper-backed, empirical
  benchmark/result-backed, production field-report-backed, or editorial
  inference.
- A strong engineer can read the first page, trust the evidence, explain the
  mechanism to someone else, and leave with one concrete prompt or agent-design
  improvement.
- The existing `/map` remains obstacle/solution-oriented; Foundations links to
  related wiki topics but does not require those topics to be the source of truth.
- The Playbook can link to a Foundation concept when a card depends on a durable
  mechanism explanation.
- Static rendering, API serving, Vercel bundling, sitemap, and shared site chrome
  all include the new surface.
- A repeatable `foundations-curator` agent routine exists for gathering
  references, writing pages, validating claims, and publishing updates.
- Repository-owned routine config exists under `.agents/routines/`, with
  scheduler-only `harness.yaml` separated from the agent-visible `prompt.md`.

## Non-goals

- Build comments, community profiles, agent cards, or an agent shop in this
  plan.
- Create a generic beginner LLM course or prompt-tip library.
- Avoid technical depth to make pages easier for casual readers.
- Re-enable LLM calls inside the deterministic hourly pipeline.
- Personalize learning paths per reader.
- Replace the existing knowledge map or Playbook.

## Architecture Decisions

### 1. Foundations gets its own source tree

Canonical authored content lives under:

```text
data/foundations/
  concepts/
    prompt-reliability.md
  references.json
  index.json
  input/
```

`data/foundations/concepts/*.md` is the source of truth. A deterministic compiler
validates those files and emits `data/foundations/index.json`, which the API and
renderers read.

### 2. Pages are concept/explanation oriented

Each page starts from a builder question and uses a stable structure:

- `Builder consequence`
- `Short answer`
- `Builder model`
- `Mechanism`
- `Math intuition`
- `Evidence`
- `How to apply`
- `Failure modes`
- `Related`

This keeps Foundations distinct from `/map`:

- Foundations: "what is the mechanism and why does it behave this way?"
- Map: "what problem am I facing and what solution families exist?"
- Playbook: "what concrete change should I try?"

### 3. Evidence is first-class

Foundation pages must track evidence explicitly. Evidence can include:

- `theory-paper` — established theory or paper-backed mechanism.
- `benchmark-result` — empirical benchmark or result with clear methodology.
- `production-field-report` — engineering postmortem, production write-up, or
  measured field report.
- `primary-doc` — official model, platform, or framework documentation.
- `editorial-inference` — LLM Digest's practical interpretation, clearly labeled
  as such and never used for unsupported quantitative claims.
- `story` — existing durable story `sid` from `data/stories/index.json`.
- `storyline` — existing storyline slug.

The compiler should validate internal references (`story` and `storyline`) and
well-formed external reference metadata. It should not try to adjudicate truth;
the curator skill owns that judgment.

### 4. Guidance is opinionated, explanations are careful

Mechanism and evidence sections stay source-grounded and precise. The
application layer should be more decisive: what an agent builder should do,
what to test, and what mistake to avoid. Pages should not flatten established
research, benchmark results, production observations, and editorial judgment
into one undifferentiated voice.

### 5. The first vertical slice is one excellent page

Ship the smallest complete reader path first:

```text
data/foundations/concepts/prompt-reliability.md
    -> pipeline/build_foundations.py
    -> data/foundations/index.json
    -> api/foundations.js
    -> web/foundations.html
    -> web/foundations/<slug>.html
```

The first page sets the editorial bar before expanding to more topics.

### 6. The curator routine writes slowly, not daily

Create `.agents/skills/foundations-curator/`. It should gather candidate topics
from feed items, wiki deltas, Playbook cards, and storylines, then update stable
concept pages when there is enough evidence. This is closer to wiki curation
than recap production.

Add a repository-owned routine definition under `.agents/routines/` after the
skill and input bundle exist. The routine should likely run weekly at first,
not daily: Foundation pages need evidence review and synthesis depth, and weak
or frequent updates would hurt the authority layer. The scheduler metadata stays
in `harness.yaml`; the agent receives only `prompt.md`, following the existing
routine convention.

## Reader Experience

Top-level nav label: `Foundations`.

Browse grouping should move toward:

- Catch up: Feed, Daily, Weekly
- Follow: Storylines
- Build: Playbook, Map, Foundations
- More: Voices, Subscribe

The `/foundations` index should be dense and useful, not a landing page. It
should show concept clusters and compact cards:

- Prompting and instruction following
- Retrieval and grounding
- Tool use and agents
- Memory and context
- Evals and reliability
- Cost, latency, and operations

Each concept page should make the answer scannable:

1. Builder consequence and short answer at the top.
2. Mechanism explanation with enough technical depth for strong engineers.
3. Optional math intuition that makes the mechanism easy to reason about.
4. Evidence list with source tiers clearly labeled.
5. Opinionated apply/failure-mode section that points to Playbook and Map.

## Data Contract Sketch

Markdown front matter:

```yaml
---
slug: prompt-reliability
title: "What makes a prompt reliable?"
question: "What makes a prompt reliable?"
summary: "Reliable prompts reduce ambiguity, constrain outputs, and make failures measurable."
status: active
cluster: prompting
updated: 2026-06-25
audience: "strong-software-engineer"
math_depth: intuition
related_topics: [instruction-following, evaluation]
related_playbook_cards: []
related_storylines: []
evidence:
  - id: brown-2020-language-models
    kind: theory-paper
    title: "Language Models are Few-Shot Learners"
    url: "https://arxiv.org/abs/2005.14165"
    note: "Introduced broad few-shot prompting behavior in large language models."
  - id: story-9022c498f1c24442
    kind: story
    sid: "9022c498f1c24442"
covers_evidence:
  - brown-2020-language-models
  - story-9022c498f1c24442
---
```

Compiled index shape:

```json
{
  "generated_at": "2026-06-25T00:00:00Z",
  "clusters": [
    {"slug": "prompting", "label": "Prompting and instruction following"}
  ],
  "concepts": {
    "prompt-reliability": {
      "slug": "prompt-reliability",
      "title": "What makes a prompt reliable?",
      "question": "What makes a prompt reliable?",
      "summary": "...",
      "cluster": "prompting",
      "audience": "strong-software-engineer",
      "math_depth": "intuition",
      "sections": [{"heading": "Short answer", "html": "..."}],
      "evidence": [{"kind": "theory-paper", "title": "...", "url": "..."}],
      "related_topics": [{"slug": "instruction-following", "title": "..."}]
    }
  }
}
```

## Dependency Graph

```text
Schema contract
    -> Markdown source page
    -> Compiler and validator
        -> API function
        -> Static renderer
            -> Web shell and detail pages
            -> Site chrome, sitemap, Vercel includeFiles
    -> Curator skill
        -> Input builder
        -> Ongoing publishing routine
```

## Task List

### Phase 1: Product and Schema Contract

#### Task 1: Write the Foundations product contract

**Description:** Add a product spec defining the audience, content bar, page
structure, evidence requirements, and relationship to Map and Playbook.

**Acceptance criteria:**
- [ ] `docs/product-specs/foundations.md` defines the section's job and
  non-goals.
- [ ] The spec rejects generic beginner education and prompt-tip listicles.
- [ ] The spec defines the authority-layer goal: trust, mechanism understanding,
  and practical builder improvement.
- [ ] The spec states the target reader: strong software engineer with high math
  capacity, not necessarily an ML researcher.
- [ ] It defines the first 6-10 candidate topics and the first shipped page.

**Verification:**
- [ ] Review against `AGENTS.md` Product Positioning.

**Dependencies:** None.

**Files likely touched:**
- `docs/product-specs/foundations.md`
- `docs/design-docs/decision-log.md`

**Estimated scope:** Small.

#### Task 2: Define the Foundation schema

**Description:** Create a schema contract for concept markdown pages and the
compiled `index.json`.

**Acceptance criteria:**
- [ ] `config/foundations_schema.md` defines front matter, allowed clusters,
  section headings, evidence kinds, and invariants.
- [ ] Required/expected sections include `Builder consequence`, `Mechanism`,
  optional `Math intuition`, `Evidence`, `How to apply`, and `Failure modes`.
- [ ] Evidence tiers are explicit: `theory-paper`, `benchmark-result`,
  `production-field-report`, `primary-doc`, `editorial-inference`, `story`, and
  `storyline`.
- [ ] The schema explains how pages link to wiki topics, Playbook cards,
  stories, and storylines.
- [ ] The schema includes a complete `prompt-reliability.md` skeleton.

**Verification:**
- [ ] Schema review confirms every field can be validated deterministically or
  is explicitly editorial.

**Dependencies:** Task 1.

**Files likely touched:**
- `config/foundations_schema.md`

**Estimated scope:** Small.

### Checkpoint: Contract

- [ ] Owner accepts the page shape and evidence bar.
- [ ] No implementation begins until the source-of-truth split is accepted.

### Phase 2: Minimal Data and Compiler

#### Task 3: Seed the first Foundation page

**Description:** Write `data/foundations/concepts/prompt-reliability.md` as the
quality-bar page.

**Acceptance criteria:**
- [ ] Page answers "What makes a prompt reliable?" for agent builders.
- [ ] It includes the required sections from the schema.
- [ ] Every evidence entry is a real source or an existing repo story/storyline.
- [ ] It clearly separates established mechanism, measured evidence, production
  observation, and editorial inference.
- [ ] It includes math intuition that explains why prompt structure changes model
  behavior without requiring research-paper notation.
- [ ] It ends with at least one concrete change a builder can make to prompt or
  agent design.
- [ ] It links to at least one relevant `/topic/<slug>` when available.

**Verification:**
- [ ] Manual source review: no unsupported quantitative claims.
- [ ] Manual reader review: a strong engineer can explain the mechanism and name
  one applicable improvement after reading.

**Dependencies:** Task 2.

**Files likely touched:**
- `data/foundations/concepts/prompt-reliability.md`
- `data/foundations/references.json` if references are centralized.

**Estimated scope:** Medium.

#### Task 4: Build the deterministic compiler

**Description:** Add `pipeline/build_foundations.py`, modeled after
`pipeline/build_wiki.py`, to parse markdown, validate references, render safe
HTML sections, and write `data/foundations/index.json`.

**Acceptance criteria:**
- [ ] `python pipeline/build_foundations.py --check` validates without writing.
- [ ] Normal build writes `data/foundations/index.json`.
- [ ] Invalid slugs, duplicate concepts, missing required sections, unresolved
  story sids, and unresolved storyline slugs fail the build.
- [ ] External references require `kind`, `title`, and `url`.

**Verification:**
- [ ] Unit tests cover success and validation failure cases.
- [ ] `python pipeline/build_foundations.py --check`.

**Dependencies:** Task 3.

**Files likely touched:**
- `pipeline/build_foundations.py`
- `tests/test_foundations_build.py`
- `data/foundations/index.json`

**Estimated scope:** Medium.

### Checkpoint: Compiled Artifact

- [ ] `data/foundations/index.json` is deterministic and reviewable.
- [ ] The first page can be served from compiled data without reading markdown
  at request time.

### Phase 3: Reader Surface

#### Task 5: Add API and Vercel bundling

**Description:** Add `/api/foundations` to serve the compiled index and individual
concepts.

**Acceptance criteria:**
- [ ] `GET /api/foundations` returns the full index.
- [ ] `GET /api/foundations?slug=prompt-reliability` returns one concept.
- [ ] Invalid slugs return 400; unknown slugs return 404.
- [ ] `vercel.json` includes the necessary `data/foundations/index.json` bundle.

**Verification:**
- [ ] API tests or a node harness exercise list, detail, invalid, and missing
  cases.

**Dependencies:** Task 4.

**Files likely touched:**
- `api/foundations.js`
- `vercel.json`
- `tests/test_foundations_api.py` or equivalent JS harness.

**Estimated scope:** Small.

#### Task 6: Add the `/foundations` index and concept pages

**Description:** Build the reader-facing shell and generated static detail pages.

**Acceptance criteria:**
- [ ] `/foundations` shows concept clusters and links to concept details.
- [ ] `/foundations/<slug>` renders the compiled concept page.
- [ ] The page uses shared site chrome and respects mobile constraints.
- [ ] `pipeline/render_static_pages.py` generates static concept pages and
  sitemap entries.
- [ ] `scripts/vercel_build.py` rebuilds Foundations before staging output.

**Verification:**
- [ ] Static renderer test covers the index and one detail page.
- [ ] Browser QA checks desktop and mobile widths for non-overlap and readable
  hierarchy.

**Dependencies:** Task 5.

**Files likely touched:**
- `web/foundations.html`
- `pipeline/render_static_pages.py`
- `scripts/vercel_build.py`
- `tests/test_foundations_surface.py`
- `web/site-chrome.js`
- `web/site-chrome.css` if navigation grouping needs styling.

**Estimated scope:** Medium.

#### Task 7: Cross-link from existing surfaces

**Description:** Make Foundations discoverable from the surfaces that naturally
need concept explanations.

**Acceptance criteria:**
- [ ] Site chrome includes `Foundations` under the Build group.
- [ ] `/map` topic pages can show related Foundation concepts when present.
- [ ] Playbook cards can link to `foundation_url` without breaking existing
  cards.
- [ ] Daily/weekly recap overlays do not duplicate Foundation content; they only
  link when useful.

**Verification:**
- [ ] Existing wiki and Playbook tests still pass.
- [ ] One fixture proves a topic can link to a Foundation concept.

**Dependencies:** Task 6.

**Files likely touched:**
- `web/site-chrome.js`
- `pipeline/render_static_pages.py`
- `.agents/skills/playbook/SKILL.md`
- `pipeline/build_wiki.py` or topic renderer logic, if related concepts are
  compiled into topic data.
- `tests/test_wiki_surface.py`
- `tests/test_playbook_surface.py`

**Estimated scope:** Medium.

### Checkpoint: First Public Slice

- [ ] `/foundations` and `/foundations/prompt-reliability` work locally.
- [ ] Sitemap and Vercel preview include the new pages.
- [ ] Owner reviews the initial page before expanding to more topics.

### Phase 4: Curator Skill

#### Task 8: Create the `foundations-curator` skill

**Description:** Add an agent routine that can gather topic candidates and write
or update Foundation pages according to the schema.

**Acceptance criteria:**
- [ ] `.agents/skills/foundations-curator/SKILL.md` explains the routine,
  evidence bar, page contract, validation, and publishing steps.
- [ ] The skill explicitly says Foundations is concept/explanation memory, not
  obstacle/solution map content and not Playbook action cards.
- [ ] The skill requires primary or high-quality empirical evidence before
  creating new pages, and labels editorial inference separately.
- [ ] The skill requires the page to teach math intuition plainly when math is
  central to the mechanism.

**Verification:**
- [ ] Dry run against the first page instructions produces no schema conflicts.

**Dependencies:** Task 2 and Task 4.

**Files likely touched:**
- `.agents/skills/foundations-curator/SKILL.md`

**Estimated scope:** Small.

#### Task 9: Build a Foundations input bundle

**Description:** Add a helper script that collects candidate concepts from recent
stories, storylines, wiki deltas, Playbook cards, and existing Foundation
coverage.

**Acceptance criteria:**
- [ ] Script writes `data/foundations/input/latest.json`.
- [ ] Bundle includes candidate source stories, related wiki nodes, related
  Playbook cards, existing concepts, and staleness hints.
- [ ] It does not automatically create or edit published concept pages.

**Verification:**
- [ ] Run the script and inspect a small candidate bundle.

**Dependencies:** Task 8.

**Files likely touched:**
- `.agents/skills/foundations-curator/scripts/build_foundations_input.py`
- `data/foundations/input/latest.json` generated, not bundled.

**Estimated scope:** Medium.

#### Task 10: Add repository-owned routine config

**Description:** Add the external scheduler definition for Foundations curation,
following the existing `.agents/routines/<routine>/{harness.yaml,prompt.md}`
pattern.

**Acceptance criteria:**
- [ ] `.agents/routines/foundations-curator-weekly/harness.yaml` defines a
  stable id, human-readable name, description, schedule, cloud execution,
  repository slug, default branch, git-push permission, and `prompt_file`.
- [ ] `.agents/routines/foundations-curator-weekly/prompt.md` contains only
  agent-visible instructions: contracts to read, bundle command, curation rules,
  validation commands, allowed outputs, staging paths, commit message, and
  reporting requirements.
- [ ] The first schedule is conservative, likely weekly, and explicitly avoids
  daily churn unless future evidence shows the section needs it.
- [ ] The prompt requires reading `.agents/routines/COMMON.md`, `AGENTS.md`,
  `.agents/skills/foundations-curator/SKILL.md`, and
  `config/foundations_schema.md` before acting.
- [ ] The routine stages only `data/foundations/`, generated Foundation pages,
  `web/sitemap.xml`, and any explicitly regenerated index assets.

**Verification:**
- [ ] Compare `harness.yaml` against `.agents/routines/README.md`.
- [ ] Compare `prompt.md` against `wiki-curator-daily` and `playbook-weekly`
  for separation of scheduler metadata from agent instructions.

**Dependencies:** Tasks 8 and 9.

**Files likely touched:**
- `.agents/routines/foundations-curator-weekly/harness.yaml`
- `.agents/routines/foundations-curator-weekly/prompt.md`
- `.agents/routines/README.md` only if the routine catalog needs updating.

**Estimated scope:** Small.

#### Task 11: Document the routine and promotion path

**Description:** Update repo docs so future agents know Foundations exists and
how it is maintained.

**Acceptance criteria:**
- [ ] `AGENTS.md` repository index mentions `data/foundations/`,
  `/foundations`, `api/foundations.js`, the curator skill, and the routine
  config.
- [ ] `docs/PLANS.md` or `docs/BACKLOGS.md` records future expansion items such
  as comments, agent cards, and field reports as separate phases.
- [ ] Decision log records the source-of-truth decision.

**Verification:**
- [ ] Documentation references match actual routes and file paths.

**Dependencies:** Tasks 6, 8, and 10.

**Files likely touched:**
- `AGENTS.md`
- `README.md` if it has a docs/surface index.
- `.agents/routines/foundations-curator-weekly/`
- `docs/PLANS.md` or `docs/BACKLOGS.md`
- `docs/design-docs/decision-log.md`

**Estimated scope:** Small.

### Checkpoint: Repeatable Publishing

- [ ] A future agent can update Foundation pages by reading only the skill and
  schema.
- [ ] The external scheduler has a version-controlled routine definition with
  `harness.yaml` and `prompt.md`.
- [ ] Validation catches broken references before publish.

### Phase 5: Expand Carefully

#### Task 12: Add the next 5-9 seed topics

**Description:** Expand from the first page to a useful Foundations index without
diluting quality.

**Candidate topics:**
- Why does adding more context sometimes hurt?
- When should I use RAG instead of fine-tuning?
- What should an agent eval measure?
- Why do tool-calling agents make weird mistakes?
- Why do agents fail at long-horizon tasks?
- What does memory mean in an agent system?
- How should builders think about hallucination?
- How do latency and cost constraints change agent design?

**Acceptance criteria:**
- [ ] Each page has enough evidence to justify publication.
- [ ] Thin topics stay as backlog candidates, not published stubs.
- [ ] The index remains finishable and scannable.

**Verification:**
- [ ] `python pipeline/build_foundations.py --check`.
- [ ] Browser QA of the index and representative detail page.

**Dependencies:** Task 10.

**Files likely touched:**
- `data/foundations/concepts/*.md`
- `data/foundations/index.json`

**Estimated scope:** Medium per 2-3 topics.

## Validation Matrix

| Area | Validation |
|---|---|
| Schema | `python pipeline/build_foundations.py --check` |
| Static rendering | `python pipeline/render_static_pages.py` |
| Vercel build | `python3 scripts/vercel_build.py` |
| API | list/detail/invalid/missing API tests |
| Existing surfaces | wiki, Playbook, daily, weekly surface tests |
| Browser | desktop and mobile screenshots for `/foundations` and one detail page |
| Content quality | manual evidence review for unsupported claims |
| Authority bar | strong-engineer review for trust, mechanism understanding, and one concrete application |

## Rollout Plan

1. Land product/schema docs.
2. Build the first complete vertical slice with `prompt-reliability`.
3. Review a local or Vercel preview before adding more topics.
4. Add the curator skill and input bundle after the first page proves the schema.
5. Add the repository-owned weekly routine config.
6. Expand to 6-10 topics over several curation runs.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Generic beginner content dilutes positioning | High | Page titles must be builder questions; spec rejects prompt-tip content. |
| Claims become unsourced or overconfident | High | Evidence metadata, validator checks for references, manual review for quantitative claims. |
| Math becomes performative or intimidating | Medium | Keep math as intuition-first and optional; use it only when it improves builder judgment. |
| Foundations duplicates the wiki | Medium | Keep separate schemas: concepts/explanations vs obstacles/solutions. Cross-link, do not merge. |
| New section bloats navigation | Medium | Place under Build in Browse; avoid adding noisy chrome controls. |
| Curator routine publishes weak pages too quickly | Medium | Require enough evidence; keep thin topics in input/backlog until ready. |
| Vercel misses data files | Medium | Add `api/foundations.js` includeFiles and test preview build. |

## Open Questions

1. Should the first public label be `Foundations`, `Agent Foundations`, or
   `Learn`? Current recommendation: `Foundations`.
2. Should Foundation detail pages be generated static-only, API-backed shell-only,
   or both? Current recommendation: both, matching recap/wiki durability.
3. Should external references be centralized in `references.json`, embedded in
   each page, or both? Current recommendation: embed first, centralize only if
   duplication becomes painful.
4. Should comments attach to Foundation pages later? Recommendation: yes, but
   only after structured field reports or agent cards exist.

## Future Phases Outside This Plan

- Builder field reports attached to Foundation concepts.
- Agent cards with evidence-backed outcomes.
- Comments on concrete artifacts: Foundation pages, Playbook cards, storylines,
  and agent cards.
- Agent shop or marketplace once agent cards and trust signals mature.
