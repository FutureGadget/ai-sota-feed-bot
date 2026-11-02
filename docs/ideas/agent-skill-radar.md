# Skill Radar (`/skills`)

Status: brainstorm one-pager + four measured feasibility probes (2026-11-01).
Scope: discovery and ranking only. No install prompts, no verification
containers, no harness install contract. Not admitted to `PLANS.md` yet.

## Decided (2026-11-01)

- Scope is discovery and ranking. Installation is explicitly out.
- Capability groups the board; practitioner is a first-class label plus its own
  lane.
- Two ranking models with separate scores, `Rising` and `Shelf`. Not one score
  with different filters.
- Discovery is a union of channels with provenance. Topics are a small-repo
  channel only, because tags anti-correlate with traction.
- The traction unit is the name family. `fork_ratio` is the adoption proxy,
  because installing a skill means copying it.

## Implementation Status (2026-11-01, Phase 1 shipped)

Built and running:

- `pipeline/collect_skills.py` with `pipeline/../config/skills.yaml`, 29 tests in
  `tests/test_collect_skills.py`, and `.github/workflows/skills-refresh.yml`
  (6-hourly, own failure domain, `git_commit_runtime.sh` for the data commit).
- Live run: **1,192 repos**, **20,587 deduped skills** from 62,192 raw
  `SKILL.md` paths, **1,179 families** (11 multi-member), 2,474 requests in
  ~20 minutes. Harness vendoring was the big inflator: one repo (`impeccable`)
  vendors the same skill 15 times, and one German-legal repo ships 18,980
  `SKILL.md` files.
- Board: 324 on-lens families (419 off-lens excluded by the lens gate), shelf 24,
  rising 4, 16 capability groups.

What works already:

- discovery union + provenance, exact `SKILL.md` basename matching, per-harness
  dedupe with `copies`/`layouts`/`locales`, family clustering (skill-name
  containment + explicit pointers, with a name-token gate that stopped
  `morluto/rea` absorbing unrelated repos), separate Rising/Shelf models,
  shelf hysteresis, fork-ratio adoption with a cap, and an LLM-assignment hook
  with a content-hash cache.

What changed after the first live pass:

- **The capability board no longer needs a caveat.** `provisional` is gone. A
  group appears only when at least two skills in the setup name that capability
  (`capabilities.min_matching_skills`, aggregated inventories excluded), keyword
  matching is word-bounded (`memo` no longer matches "memory", `paper` no longer
  matches "paperclip"), and the most focused setup wins the group rather than
  the one with the most matches. That surfaced vendor collections over dumps:
  `microsoft/azure-skills` for infra, `openai/codex-security` for security,
  `google/agents-cli` for tooling. The optional cached LLM pass is still
  available and still unset; the board does not depend on it.
- **UI/UX pass (2026-11-02).** Board order is Rising, By capability, Reference
  shelf, Practitioners (the practitioner lane only renders when at least two
  entries have real ports). The shelf shows the dominant capability plus a group
  count, lens badges, and an inline port count, and tables stack into labelled
  rows under 760px. The feed carries a three-card `Skill Radar · rising this
  week` strip in `web/skills-strip.{css,js}` reading `web/skills-top.json`; it
  starts hidden and stays hidden if the artifact is missing.
- **Rising is nearly empty on purpose.** It requires a velocity baseline or new
  port repos, and there is exactly one history snapshot so far. It fills over the
  first week of 6-hourly runs.
- **Community/practitioner weighting is unvalidated.** Port counts work for
  `pstack` (2) but the practitioner lane currently ranks by aggregate stats, not
  by verified independent ports.
- No page, no API, no recap integration yet. `/skills` is Phase 2.

### Phase 2a shipped (2026-11-02): the board is live

- `/skills` and `/skills/<family>` are pre-rendered by
  `render_static_pages.py` (`render_skills_page`, `render_skill_pages`) from
  `data/skills/latest.json`. 50 family pages were generated for the families the
  board actually references; the rest stay in the artifact.
- Served payloads are static: `web/skills-data.json` (66 KB) and
  `web/skills-top.json` (the 3-card slice the feed strip will use). No API
  route, no R2 key, no function budget: under the Cloudflare Worker, `public/`
  assets are unmetered and served before the Worker runs.
- Routes were added to **both** `vercel.json` (`rewrites`) and
  `worker/src/index.js` (`STATIC_REWRITES`). They are separate copies, and an
  unmatched path has no asset fallback, so a route in one place only would 404
  silently. `tests/test_skills_pages.py` now asserts parity for `/skills`.
- Nav: `SITE_DESTINATIONS` for generated pages plus the hand-edited shells.
- Capability groups render with an honest note while `provisional` is true.

Storage policy (decided 2026-11-02, after a size check):

- **No skill content is ever stored.** `collect_skills.py` reads tree listings
  only; it never fetches `SKILL.md` bodies. The census holds a name and a copy
  count per skill, plus repo-level stats.
- Slimming: dropping per-skill paths/shas/layouts/locales took
  `repos.json` from 6.5 MB to 2.3 MB (roughly a 400 KB git blob), with identical
  board output.
- Retention: `retention_days: 45` drops repos no sweep has seen, and
  `history_retention_days: 90` prunes star snapshots. Without both, a 6-hourly
  append-only job would grow the repository forever.
- Context cost and better capability labels would need frontmatter, so if they
  land they must be stored as derived numbers (token count, capability), never
  as the body text.

## Problem Statement

An agent engineer now picks skills the way they pick models: something goes
viral, and the question is "is it real, what does it cost me, and does it still
work?" Today the answer is scattered across GitHub repos, awesome-lists, and
screenshots. awesome-lists rank by nothing and often point at repos that contain
no skill at all; star counts are repo-level, cumulative, and inflated; nobody
publishes what a skill costs in context tokens.

Skill Radar is the `/models` equivalent for skills: a lens-filtered, capability-
grouped catalog where momentum comes from our own snapshots and every claim
links to a primary source.

It is a *directory* risk: directories do not earn returning readers. The
retention play is freshness (what rose this week) plus a weekly email section,
judged against the north star, not novelty.

## Probe Results (2026-11-01, live GitHub API)

Scripts: `/tmp/skill_census*.py`, `/tmp/skill_probe2.py`, `/tmp/skill_probe3.py`,
`/tmp/skill_census3.json`, `/tmp/skill_sample.json`. Uncommitted throwaways.

### Code search is not a usable census

| Probe | Result |
|---|---|
| `search/code q=filename:SKILL.md` `total_count` | 6,651,904 (identical for `filename:skill.md`, so the counter is saturated and unreliable) |
| files reachable | 1,000 (hard cap) from **750 repos** |
| canonical repos found | **none**: `anthropics/skills`, `obra/superpowers`, `vercel-labs/agent-skills`, `openai/codex` absent |
| precision | the hits are real `SKILL.md` files, but many belong to non-skill products (an MPD client, a Spark flow engine, an MCP server) |

`filename:` is tokenized, not exact. 6.6M fuzzy matches consume the 1,000-result
budget before anything popular surfaces. Useful only as a long-tail supplement
once the repo list exists.

### Repo search finds canonical repos, but tags anti-correlate with traction

Calibration set: `pstack` and `hallmark` are the two skills a human named as
recently taking off. Both were checked against the live API.

| Query | Repos | >=1000 stars | >=20 stars |
|---|---|---|---|
| `topic:agent-skills` | 39,984 | 299 | 2,597 |
| `topic:claude-skills` | 13,810 | 124 | 1,222 |
| `topic:claude-code-skills` | 2,422 | 35 | 278 |
| `"agent skills" in:name` | 13,593 | 22 | 394 |
| `"claude skills" in:name` | 10,321 | 13 | 198 |
| `"SKILL.md" in:readme` | 469,176 | 962 | 15,232 |

Canonical repos appear immediately (`anthropics/skills` 186k stars is the #2 hit
for `topic:agent-skills`). Per-repo enumeration is exact via
`git/trees?recursive=1`: one request per repo, no truncation at this scale.

### Calibration: tag-based discovery finds the wrong repos

| repo | stars | fork% | age | stars/day | topics | unique skills | body tok p50 |
|---|---|---|---|---|---|---|---|
| `mattpocock/skills` | 309,035 | 8.4% | 271 | 1,140 | **0** | 39 | 860 |
| `Nutlope/hallmark` | 44,561 | 5.3% | 187 | 238 | **0** | 1 | 4,442 |
| `garrytan/gstack` | 138,559 | 14.8% | 234 | 592 | **0** | 39 | 5,102 |
| `anthropics/skills` | 186,209 | 11.8% | 405 | 460 | 1 | 20 | 1,882 |
| `obra/superpowers` | 310,471 | 8.9% | 387 | 802 | 8 | 15 | 1,892 |
| `backnotprop/pstack` | 3,315 | 7.1% | 158 | 21 | 12 | 40 | 722 |
| `michael-denyer/pstack-claude` | 3,718 | 9.2% | 159 | 23 | 20 | 40 | 526 |
| `addyosmani/agent-skills` | 112,474 | 10.5% | 258 | 436 | 6 | 25 | 3,301 |

Four findings that change the discovery design:

1. **Topic tags anti-correlate with traction.** The biggest repos in the set carry
   zero topics (`mattpocock/skills` 309k stars, `gstack` 138k, `hallmark` 44.5k)
   while the smallest are the most heavily tagged (`pstack` 12-20 topics, 3.3-3.7k
   stars). Repos that already went viral do not optimise for discovery; repos
   trying to be discovered do. A topic-first sweep surfaced the wrong 400 repos
   and missed `hallmark` entirely.
2. **Recall is a union problem.** `skill in:name,description stars:>300` (top 300)
   finds `hallmark` but not `pstack`. `agent in:name,description` finds neither.
   Only `pstack in:name` and `topic:agent-skills` find `pstack`. Momentum sweeps
   by `created:>date stars:>N` are small enough to enumerate completely (1,885
   repos for `stars:>2000 created:>2026-01-01`).
3. **The traction unit is a name family, not a repo.** 25 repos match
   `pstack in:name`, totalling 8,753 stars with a 3,718 max: `pstack-claude`,
   `open-pstack`, `t3-pstack`, `pstack-for-codex`, `pstack-codex`, `oh-my-pstack`,
   `pi-pstack`, `pstack-hermes`. `gstack` has its own port family. Renamed forks
   are the distribution mechanism, so one repo's stars understate a concept by an
   order of magnitude.
4. **Fork ratio is the adoption proxy that fits how skills are installed.** Real
   skill repos run 5.3%-14.8% forks-to-stars; ordinary libraries run 2-5%.
   Installing a skill means copying it into your own tree, so forking *is* the
   install.
5. **The dominant distribution pattern is a practitioner publishing their agent
   setup**, not a skill marketplace listing. `mattpocock/skills` is "straight from
   my `.agents` directory" (309k stars). `gstack` is "Garry Tan's exact Claude
   Code setup". `pstack` is Lauren Tan's, then ported by others. Traction follows
   the person, which is also why the biggest repos carry no tags: they do not need
   discovery. The catalog therefore needs a **practitioner/source** dimension
   (who authored it), the same way feeds track source reliability, and family
   leads cannot be picked by "the origin repo": `poteto/pstack` 404s, so the
   original may have no public repo at all.

Also: the feed corpus does not cover this layer. `pstack`, `gstack`, `poteto`, and
`superpowers` have zero mentions in `data/stories/`; `hallmark` has one. The
`reach` term cannot be a primary ranking signal for skills.

### Family detection: skill-name overlap works, description text does not

First attempt used description-token Jaccard. It failed in both directions: it
rejected `backnotprop/pstack` (the family's own 3.3k-star member) and accepted a
banquet-hall website named `hallmark-banquets`.

Verified replacement rule, tested on 16 repos across 3 families:

- **Shared skill-name set**: containment of the smaller inventory in the larger
  (`|A and B| / min(|A|,|B|)`) >= 0.30. `backnotprop/pstack` contains 0.90-1.00 of
  every port's skill names (`architect`, `arena`, `automate-me`,
  `benchmark-checklist`), so all 6 real ports cluster and both name-collision
  impostors (`peadar/pstack`, 2012 C stack traces; `bangerlee/strace_pstack`)
fail automatically: they ship **zero** skills.
- **Explicit reference fallback**: description or README names the origin ("port
  of Lauren Tan's pstack", "derived from", "via Michael Denyer's"). Needed
  because `gstack` ports rename or strip their skill dirs, so name overlap is 0
  for most of them.
- **Zero-skill repos never join a family**, which is what kills the
  banquet-hall and stack-trace false positives.
- **GitHub fork lineage is not usable here**: 0 of 16 repos carry `fork: true`,
  including ones whose description says "Fork of garrytan/gstack". Use the flag
  when present, never rely on it.

Resulting aggregates: `pstack` 7,990 stars across 7 repos sampled (25 total by name);
`gstack` 138,927 across 56; `hallmark` is a family of 1, correctly.

### The raw skill count is inflated by harness vendoring

80 most-starred repos contain **15,063 `SKILL.md` files**, but that number is
not a skill count. The same skill is vendored once per harness directory:

- `pbakaus/impeccable`: one skill, **15 copies** (`.agent/`, `.agents/`,
  `.claude/`, `.cursor/`, `.devin/`, `.dsh/`, and more)
- `DietrichGebert/ponytail`: 6 skills x 2 copies (`.openclaw/` + `skills/`)
- `thedotmack/claude-mem`: `mem-search` x 3 (one per product variant)
- plus per-locale copies (`docs/ja-JP/...`, `docs/zh-CN/...`)

Measured within-repo dedupe factors: `gstack` 71 files -> 39 unique names,
`pstack-claude` 67 -> 40, `pstack` 61 -> 40. So the census must dedupe on
`(repo, frontmatter name)` and treat the copy count as *portability* evidence,
not as skill count.

Path matching must be exact: `path.endswith("skill.md")` also matches
`verification-skill.md`, inflating `pstack` by 1, `gstack` by 5, and
`pstack-claude` by 5 (6-7% false positives). Require `basename == SKILL.md`.

One mega-collection (`ComposioHQ/awesome-claude-skills`, 78k stars) contains
**zero** `SKILL.md` files: it is a README pointer list. 7/80 topic-tagged repos
contain zero.

### The audience lens is a hard gate at two levels

14/80 top repos are off-lens and sit near the top (video generation 137k stars,
design workspace 105k, job search 79k, PPT 72k, marketing 57k). It is also off
*within* lens-classified repos: 23/140 sampled skills were off-lens. A hard gate
is required; ranking weights alone will not fix it.

### Capability taxonomy: keyword-only coverage is 66%

On a 140-skill sample across 12 lens-relevant repos, a 17-bucket keyword
classifier assigned 93/140 (66%). The rest fell in "other", including skills that
are obviously classifiable (`requesting-code-review`,
`dispatching-parallel-agents`). Roughly a third of the catalog would be
uncategorized if we rely on regex keywords alone.

### Context cost is real and badly distributed

Body size across the sample: p50 7.8 KB (~1,960 tokens), p90 18.7 KB (~4,680),
max 105 KB (~26,000 tokens). 11/140 exceed 5k body tokens. A skill that costs
26k tokens when it triggers is a decision, and nobody publishes this number.

### Distribution hygiene

- **No license**: 9/80 at the top, **373/700 (53%)** in the long tail. Display
  field, not a gate (we never redistribute).
- **Stale** (>180d without a push): 0/80 at the top, 108/700 (15%) in the tail.
- **Repackaging**: 120 sampled files across 4 mega-collections, **zero** exact
  content collisions. The inflation is vendoring and pointer lists, not copies.
- **Signal skepticism**: `morluto/rea` has 417,710 stars / 104,391 forks for 5
  skills; a 48.9k-star repo ships 8,890 auto-named skills (`007`). Star counts
  here are not organic in the 2019 sense. Publish bands plus velocity, and
  require provenance for admission.

## Discovery: a Union of Channels, No Backbone

No single query is the census. Each channel has a measured recall gap, so the
collector unions them and stores provenance per repo (`discovered_via`).

| Channel | Query shape | Finds | Misses |
|---|---|---|---|
| Momentum | `created:>date stars:>N`, `pushed:>date` | viral repos with zero topics (`hallmark`) | small tagged ones |
| Topic | `topic:agent-skills`, `topic:claude-skills` | small-and-tagged (`pstack`) | the biggest repos (0 topics) |
| Name family | `<name> in:name` for every admitted name | renamed ports (`pstack-claude`, `t3-pstack`) | unrelated concepts |
| Co-mention | repo links inside admitted skills' docs | ecosystem neighbours | solo repos |
| Pointer lists | awesome-list README extraction, then resolve | curated seeds | lists that vendor no code |
| Feed + HN | `data/stories/`, HN Algolia | already-discussed items | most of this layer |
| Reader submission | issue template | long tail | everything unreported |

Then enumerate every repo with `git/trees?recursive=1`, keep only
`basename == SKILL.md`, dedupe to `(repo_id, frontmatter_name)`, assign a
capability, gate.

Cost is fine: the momentum sweeps are small (1,885 repos for
`stars:>2000 created:>2026-01-01`), the topic queries are ~60k repos of which only
~2,600 clear 20 stars, and enumeration is one conditional request per known repo.
A 6h run polls known repos plus whatever the sweeps turn up.

## Unit of Record

**`(repo_id, frontmatter_name)`**, after deduping vendored copies, grouped into a
**name family** for traction scoring.

- `repo_id` is GitHub's immutable numeric id, so renames and transfers do not
  fork identity. `full_name` is display only.
- `frontmatter_name` beats `skill_path` as the stable within-repo key, because
  the same skill is copied across harness dirs and the path varies.
- Dedupe: group by `(repo_id, name)`, then keep the copy whose body hash is the
  majority; record `copies`, `layouts`, and `locales` as metadata.
- `practitioner` = the author surface (person or lab), displayed on every card.
  It is a quality prior and the organising axis that matches how this ecosystem
  actually distributes (see calibration finding 5).
- `family` = name-family group (`pstack` and its 25 ports) plus a same-concept
  check, because `pstack in:name` also matches a 2012 C stack-trace tool. The
  family lead is the earliest qualifying public repo that the family refers to,
  which is not always the origin: `poteto/pstack` 404s.
- `portability` = number of distinct harness layouts the skill ships for. This is
  free, deterministic, and genuinely informative in a fragmented ecosystem
  (`.claude/`, `.agents/`, `.agent/`, `.cursor/`, `.devin/`, `.dsh/`,
  `.openclaw/`, `.kiro/`, `plugins/`, `skills/`, repo root all observed).
- **Mega-collection handling**: per-repo admission cap (e.g. 25 unique skills)
  plus an `aggregated_inventory` flag when names look machine-generated (`007`,
  numeric prefixes, no per-skill README). An 8,890-entry repo is a source to
  sample, not a catalog to mirror.

## Ranking

Three stages, mirroring `ranking.py` rather than inventing a new engine.

### 1. Gate (deterministic, published)

- existence: `SKILL.md` parses with `name` + `description`
- not archived, not a fork
- lens: passes the audience classifier at the *skill* level
- hygiene: license recorded (or `no-license` flagged), inventory not beyond cap
- dedupe: one record per `(repo_id, name)`
- no topic requirement: topics are a discovery channel, never an admission
  condition, because they anti-correlate with traction

### Lens belongs to the capability, not to the keywords

The first classifier attempt used repo description + topics and labelled
`hallmark` (an anti-AI-slop *design* skill) as agent-engineering, because its
description contains "Claude Code, Cursor, Codex". Almost every skill description
names a harness, so harness tokens are non-discriminative and must be stripped
before classification. Use one taxonomy for both jobs: assign the capability
first, then read that capability's audience weight from config. A design
capability is off-lens regardless of which harness it names.

### 2. Score (config weights, explainable)

```text
score = 0.30 * family_momentum  # log(sum of family stars_7d) * 1/sqrt(family_unique_skills)
      + 0.20 * fork_ratio       # adoption proxy: forking is installing
      + 0.15 * velocity         # lead repo stars_7d, normalized by age
      + 0.15 * lens             # capability weight from config
      + 0.10 * substance        # has scripts/references; body 2-12 KB band; specific description
      + 0.05 * portability      # distinct harness layouts + port count in family
      + 0.05 * reach            # HN points + feed coverage when present (booster only)
      - penalties               # stale, aggregated inventory overflow
```

Three terms carry the measured lessons:

- `family_momentum` replaces plain repo stars. The calibration showed a concept's
  traction is spread across renamed ports: `pstack` is 3.3k stars on its lead repo
  but 8.7k across 25 repos, and would be invisible on a repo-ranked board.
- `1/sqrt(unique_skills)` is the anti-mega-collection device: a repo with 1,068
  skills gets a third of the momentum credit of a 5-skill repo with the same
  stars.
- `fork_ratio` outranks `velocity` because in this ecosystem copying *is*
  adoption.

Velocity comes from daily snapshots, so "newly famous" is measured, not scraped.
Stars are displayed as a band, plus `stars_7d`.

### 3. Lanes: two ranking models, not one score with filters

Decided 2026-11-01: capability groups the board, practitioner is a first-class
label with its own lane, and the radar and the reference shelf rank separately.

Sharing one score and filtering it differently fails in a predictable way: the
shelf fills with whatever is currently rising and empties as that fades, so
"reference" stops meaning anything.

**Rising (radar)**

```text
rising = 0.45 * velocity_7d      # stars_7d, age-normalized
       + 0.20 * family_spread   # new ports born in the last 30d
       + 0.20 * family_momentum # log(family stars_7d) * 1/sqrt(family unique skills)
       + 0.15 * novelty         # first_seen recent; not already on the shelf
       - penalties
```

- entry: velocity percentile above threshold; exit: 28d of flat velocity
- each card carries a machine-generated reason string (`+2,400 stars in 7d`,
  `3 new ports this month`, `first seen 9d ago`), same idea as the Brief's
  utility reasons
- this lane is disposable. It is allowed to be empty in a quiet week.

**Shelf (reference)**

```text
shelf = 0.30 * adoption        # family stars + forks, log-scaled
      + 0.25 * fork_ratio      # forking is installing
      + 0.20 * durability      # age, sustained push history, release cadence
      + 0.15 * breadth         # unique skills, harness coverage, port count
      + 0.10 * practitioner    # author track record
      - penalties              # churn, aggregated inventory, no license
      - stale_penalty          # >90d without a push
```

- entry requires **age >= 30d** (a two-week-old repo is not a reference, no
  matter how viral) or 1,000+ stars with fork ratio above threshold
- **hysteresis**: enter at score X, leave at X - 0.05, so entries do not flap
  week to week
- churn penalty: rapid add/remove of skills signals an unstable bundle
- this lane changes slowly on purpose. That is the product.

**Practitioners**

```text
practitioner = 0.40 * port_count      # independent repos re-implementing their setup
             + 0.35 * aggregate_adoption
             + 0.15 * breadth
             + 0.10 * recency
```

Port count is the differentiator and nothing else publishes it: Lauren Tan's
pstack has 25 named ports, Garry Tan's gstack has a port family of its own.
Someone else re-deriving your setup is a stronger signal than stars.

### Presentation

Ranking alone still produces a directory. Two card types, because the unit of
traction and the unit of presentation differ: a **family card** (`pstack`: 25
ports, 7,990 stars combined) and a **skill card** (`hallmark`: one skill, 4.4k
tokens of context). Family cards exist only when the family clears the same
gates, and the lead repo is the representative.

- **Capability groups**: one representative per capability plus up to two
  alternates, so the board says "the code-review skill worth trying", not "here
  are 40 code-review skills".
- **Quotas**: max 3 skills per repo, max 1 per capability at rank 1, source
  diversity like `editorial.yaml` role caps.
- **Practitioner label** on every card, plus the practitioners lane.

### Capability assignment needs one primary label

Multi-label keyword matching is the wrong shape for a grouping key. Measured on
the 140-skill sample with a 23-bucket taxonomy: 86% coverage, but 2.19 labels per
skill and 18 skills matching more than four buckets (`frontend-design` matching
any occurrence of "design"; `product-planning` matching "plan"). A grouped board
needs exactly one primary capability per skill.

Decision: **primary capability from a cached LLM call** through the existing
`judge.py` client, constrained to the taxonomy enum, cached by content hash so a
re-run costs nothing. Keywords stay as the offline fallback and as a prior for
prompt construction, not as the assignment. Below 95% assignment, ship an honest
"Uncategorized" group rather than guessing.

Frontmatter parsing must expand YAML block scalars: 4 of 19 "unmatched" sample
skills had `description: |-` or `>-` and were parsed as empty. Strip harness names
(`claude`, `codex`, `cursor`, `pi`) before classifying, per the lens finding.

## Reviews: Signals, Not Scores

No 1-5 rating. There is no review corpus, and an LLM-minted score is fake
precision.

1. **Derived** (no LLM): stars band + `stars_7d`, issue volume, HN points with
   thread links, feed coverage.
2. **Editorial pulse** (agent routine, shaped like `model-pulse`): 3-5 bullets
   per top capability of "what it is good at / where it breaks", each with a
   primary link; complaint themes clustered from issue titles ("token bloat, 12
   issues"). Durable sidecar with a `covers_*` snapshot for staleness.
3. **Reader reports** later, if the board earns traffic. That is where a real
   skill-level popularity signal would eventually come from, since GitHub does
   not provide one.

## Architecture

```text
.github/workflows/skills-refresh.yml      every 6h, own workflow/failure domain
  pipeline/collect_skills.py          ->  data/skills/repos.json
                                          data/skills/families.json
                                          data/skills/skills.json
                                          data/skills/practitioners.json
                                          data/skills/history/<date>.json (slim deltas)
  pipeline/build_skill_board.py       ->  data/skills/latest.json (served board)
.agents/routines/skill-pulse/         ->  data/skills/pulse/<capability>.json
pipeline/render_static_pages.py       ->  web/skills/index.html
                                          web/skill/<repo-slug>/<name>.html
config/skills.yaml                        seeds, sweep queries, capability taxonomy
                                          + audience weights, lane weights, caps,
                                          hysteresis deltas, practitioner rules
```

Artifact split follows `data/models/`: raw entity files (`repos`, `families`,
`skills`, `practitioners`) are the audit surface, `latest.json` is the only file
the page needs, and `history/` holds slim star snapshots for velocity.

**No new serverless function**: `api/` is at the 12-function Hobby cap. `/skills`
is pre-rendered with a JSON data island embedded in the shell (the `/map`
pattern), so filtering and lane switching work client-side against committed
data and crawlers see real HTML. Per-skill pages render only for admitted skills
(hundreds, not thousands).

Data commits via `scripts/git_commit_runtime.sh`; the workflow stays in its own
failure domain, like `models-refresh.yml`.

## Phasing

1. **Phase 1 - census and measure, no UI.** Seeds, repo sweep, trees
   enumeration, dedupe, lens gate, capability assignment. Ship
   `data/skills/latest.json` and stop. No page until the ranked list is one we
   would read ourselves.
2. **Phase 2 - board.** Pre-rendered `/skills` with capability board, lanes,
   momentum sparklines, context cost, source links. This is the shippable unit.
3. **Phase 3 - editorial pulse** sidecars per top capability.
4. **Phase 4 - weekly Skill Radar email section**, if Phase 2 shows retention.

## Assumptions

Answered by the probes:

- [x] Code search can enumerate the ecosystem: **no**, misses every canonical
      repo, caps at 1,000 files, unreliable `total_count`.
- [x] Repo search finds them: **yes**, via topic + `in:name`.
- [x] Topic tags can be the discovery backbone: **no**, they anti-correlate with
      traction (biggest repos carry zero topics).
- [x] Raw `SKILL.md` count is a skill count: **no**, per-harness vendoring
      inflates one skill to 15 copies.
- [x] Frontmatter is uniform enough to parse: **yes**, 10/10.
- [x] Exact repackaging is the inflation source: **no**, 0 collisions in 120
      samples; vendoring and pointer lists are.

- [x] Keyword taxonomy can be the grouping key: **no**: 86% coverage but 2.19
      labels per skill. Use one primary capability from a cached LLM call.
- [x] Family membership is detectable: **yes**, by skill-name containment >= 0.30
      plus an explicit-reference fallback; zero-skill repos never join.

Still open:

- [ ] Does the lens classifier hold up on a labeled 100-repo sample? The current
      keyword version mislabeled `firecrawl` and `MinerU` as agent-engineering,
      and labelled `hallmark` on-lens only because it names harnesses.
- [ ] Can skills *within* a mega-collection be ranked honestly at all, or is the
      answer "repo-level rank + editorial picks" until reader reports exist?
- [ ] `git/trees` cost for ~1,000 repos per 6h run with `If-None-Match`
      conditional requests, including the family sweep (`<name> in:name`).
- [ ] What counts as a shelf exit under hysteresis in a young ecosystem where
      every repo in the calibration set is under 14 months old?
- [x] Does the feed corpus (`data/stories/`) mention skills often enough for the
      `reach` term to carry real signal? **No**: zero mentions for `pstack`,
      `gstack`, `poteto`, `superpowers`; one for `hallmark`. Booster only.

## Not Doing (and Why)

- **Install prompts / verification containers / harness install contract** -
  out of scope by decision (2026-11-01). The radar answers "what should I look
  at", not "install it for me".
- **A synthetic 5-star score** - fake precision on a corpus that does not exist.
- **Scraping GitHub Trending** - no API, brittle, worse than our own deltas.
- **Ranking by absolute stars** - measured to produce a consumer-AI directory
  (video generation, job search, PPT) instead of our lens.
- **Crawling `filename:SKILL.md` as the census** - misses every canonical repo.
- **Mirroring mega-collections** - an 8,890-entry repo is a source to sample.
- **A new `/api/skills` function** - at the Hobby cap; static render is better.

## Open Questions

- Board shape: is "one representative per capability" the right centerpiece, or
  do readers want the flat ranked table with a capability filter? The Brief says
  one card per story; skills may want the same.
- Ranking axis: absolute `stars_7d` or growth relative to the repo's own
  baseline? Probably rank absolute, badge the rate outliers.
- Given star outliers (417k stars / 104k forks on a 5-skill repo), do we publish
  stars at all, or band plus velocity only?
- Do skills enter the Brief as a lane, or stay a separate catalog? Mixing them
  into the 2h edition risks the finishable brief becoming a tool directory.
