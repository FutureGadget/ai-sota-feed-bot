# Product and Engineering Backlog

Durable home for valuable ideas that are not yet implementation-ready or
scheduled. Active work belongs in `docs/exec-plans/active/`; current roadmap
summary belongs in `docs/PLANS.md`.

## Backlog contract

Use stable IDs (`BL-###`) and append new entries rather than renumbering them.
Each entry must state:

- **Status:** `idea`, `needs-spec`, `ready`, `scheduled`, or `closed`
- **Priority:** `critical`, `high`, `medium`, or `low`
- **Outcome:** the user or operational result, not a proposed implementation
- **Scope:** likely capabilities and boundaries
- **Dependencies:** prerequisites or related systems
- **Guardrails:** constraints that must survive implementation
- **Promotion criteria:** evidence needed before creating an execution plan

When an item becomes scheduled, add its execution-plan link without deleting
the backlog entry. Record meaningful scope or architecture decisions in
`docs/design-docs/decision-log.md`.

## Index

| ID | Item | Status | Priority | Dependencies |
|---|---|---|---|---|
| BL-001 | Agent-managed source pipeline | idea | critical | Source inbox/schema |
| BL-002 | Metrics-driven optimization agent | idea | critical | Metric access and definitions |
| BL-003 | Agent experimentation system | idea | high | Exposure logging and sufficient traffic |
| BL-004 | Agent Skill Lab | needs-spec | high | Experiment methodology and artifact format |
| BL-005 | Harness Field Tests | idea | high | BL-004 methodology and product access |
| BL-006 | Benchmark Decoder | idea | medium | Editorial rubric and benchmark source policy |
| BL-007 | Cost efficiency & productivity coverage lens | ready | medium | Wiki-curator routine; CTR/topic-view signals |

## BL-001 — Agent-managed source pipeline

- **Status:** idea
- **Priority:** critical
- **Outcome:** Continuously improve source coverage while preserving human
  control over what enters the production feed.
- **Scope:**
  1. A source discovery skill finds relevant candidates, deduplicates them,
     collects evidence, and writes them to a review inbox.
  2. A source review skill evaluates relevance, originality, reliability,
     freshness, feed quality, overlap, and likely ranking exposure.
  3. A source onboarding skill acts only on human-approved candidates, updates
     source configuration, and uses the existing `add-source` validation path
     to prove that each source can reach readers.
  4. A later maintenance pass may propose changes to existing source weights,
     polling, metadata, or removal through the same approval gate.
- **Dependencies:** Define the candidate inbox artifact, review states,
  deduplication key, evidence requirements, and approval handoff.
- **Guardrails:** Discovery and review must never edit `config/sources.yaml`.
  Source admission remains explicitly human-approved. Optimize for engineers
  building and operating AI systems, not general AI-news breadth.
- **Promotion criteria:** Specify the inbox schema, review rubric, approval
  workflow, source-discovery channels, operating cadence, and validation
  success criteria.

## BL-002 — Metrics-driven optimization agent

- **Status:** idea
- **Priority:** critical
- **Outcome:** Use actual product and delivery evidence to improve ranking,
  content, acquisition, retention, newsletter performance, reliability, and
  site performance.
- **Scope:**
  - Join relevant signals from PostHog, Cloudflare, Resend, and Vercel.
  - Produce recurring reports with metric definitions, provenance, trends,
    anomalies, and segmented funnel/retention/content/source findings.
  - Propose prioritized config, algorithm, content, and distribution changes
    with expected impact and explicit guardrail metrics.
  - Evaluate approved changes before and after deployment, clearly separating
    correlation from credible causal evidence.
- **Dependencies:** API/data access, secret handling, shared time windows and
  identities where possible, metric dictionary, data-quality checks, baseline
  dashboards, and BL-003 for controlled experiments.
- **Guardrails:** This is broader than the current v1.3 PostHog-driven
  source-weight tuning. Do not optimize a single engagement metric at the
  expense of finishability, trust, source quality, or memory. Initial changes
  require human approval and must remain reversible.
- **Promotion criteria:** Inventory available metrics and retention limits;
  define the north-star, input, and guardrail metrics; establish data-quality
  thresholds; choose the first narrow decision this routine will improve; and
  define an approval and rollback workflow.

## BL-003 — Agent experimentation system

- **Status:** idea
- **Priority:** high
- **Outcome:** Let agents evaluate product changes with controlled evidence
  instead of relying only on sequential before/after comparisons.
- **Scope:** Stable variant assignment, exposure logging, experiment registry,
  primary and guardrail metrics, minimum sample and duration rules, analysis,
  stopping policy, and rollback support.
- **Dependencies:** Reliable event instrumentation, metric definitions from
  BL-002, privacy review, and enough eligible traffic to produce useful results.
- **Guardrails:** No peeking-driven conclusions, silent metric switching, or
  autonomous rollout of harmful variants. Preserve one trustworthy editorial
  product rather than creating opaque personalized ranking bubbles.
- **Promotion criteria:** Demonstrate sufficient traffic for a realistic test,
  define the assignment unit and exposure event, document statistical decision
  rules, and select a low-risk first experiment.

## BL-004 — Agent Skill Lab

- **Status:** needs-spec
- **Priority:** high
- **Outcome:** Help engineers building agents understand how a reusable skill or
  instruction set changes agent behavior, not merely the final answer, through
  reproducible trajectory-level experiments that create recurring reasons to
  return and subscribe.
- **Scope:**
  1. Select one public agent skill with a concrete behavioral claim.
  2. Run a fixed task under at least three conditions: no skill, a minimal
     instruction baseline, and the complete skill.
  3. Compare task success, trajectory shape, tool use, recovery behavior,
     unnecessary work, latency, token usage, and cost across repeated runs.
  4. Publish the task, environment, model and skill versions, instructions,
     evaluation rubric, representative trajectories, limitations, and a
     practical recommendation.
  5. Package experiments as a recurring editorial series with a subscription
     call to action and durable links to reproducibility artifacts.
- **Dependencies:** Define a versioned experiment manifest, task fixtures,
  repeat-run policy, evaluation rubric, artifact retention policy, and
  analytics events for return visits, subscriptions, and artifact engagement.
- **Guardrails:** Do not infer general superiority from a single task or run.
  Separate observed behavior from interpretation; disclose failures and
  experimenter judgment; preserve prompts and versions needed to reproduce the
  result. Cover skills for engineering agent systems, not prompt-tip content
  for general users.
- **Promotion criteria:** Specify the first three skill experiments, including
  one candidate such as
  [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills);
  define the common task and metrics; estimate per-edition execution cost; and
  establish baseline retention, subscription, and artifact-click metrics.

## BL-005 — Harness Field Tests

- **Status:** idea
- **Priority:** high
- **Outcome:** Help engineers choose an agent harness based on verified workflow
  capabilities and constraints rather than product descriptions or generic
  feature matrices.
- **Scope:**
  - Compare harnesses on realistic jobs such as repository changes, browser
    operation, scheduled tasks, cloud or remote execution, parallel work,
    isolation, and recovery after failure.
  - Publish job-specific conclusions such as "best fit for unattended scheduled
    work" instead of naming one universal winner.
  - Record product version, plan, environment, configuration, task fixture,
    observed trajectory, human intervention, completion quality, latency, and
    cost.
  - Re-run or clearly expire findings when relevant capabilities change.
- **Dependencies:** Reuse the BL-004 experiment manifest and reporting format;
  obtain comparable product access; define a capability-change watch and
  retest policy; identify legally and operationally safe test repositories and
  accounts.
- **Guardrails:** Test claimed capabilities hands-on. Distinguish unsupported,
  unavailable on the tested plan, and not discovered. Do not reduce nuanced
  workflow fit to a single leaderboard score, and do not present stale findings
  as current.
- **Promotion criteria:** Select two harnesses and one high-value workflow for
  a pilot; define parity rules for model, permissions, context, and budget;
  document the update/expiry policy; and validate that the expected reader
  value justifies recurring access and execution costs.

## BL-006 — Benchmark Decoder

- **Status:** idea
- **Priority:** medium
- **Outcome:** Help agent and platform engineers understand what an LLM or agent
  benchmark score does—and does not—say about a practical engineering
  decision.
- **Scope:**
  - Explain one benchmark at a time: task construction, scoring, expected
    meaning of a high score, important limitations, contamination risk, and
    sensitivity to prompts, tools, and harness design.
  - Connect benchmark results to specific engineering decisions and identify
    cases where a local task-specific evaluation is more informative.
  - Use benchmark explainers to support Skill Lab and Harness Field Test
    methodology rather than operating a general model leaderboard.
- **Dependencies:** Establish an official-source-first citation policy,
  benchmark selection rubric, version/update handling, and a compact explainer
  template.
- **Guardrails:** Do not republish leaderboard numbers without context. Avoid
  universal "best model" conclusions, unsupported score comparisons across
  benchmark versions, and beginner-oriented general LLM education that dilutes
  the site's practical engineering focus.
- **Promotion criteria:** Choose three benchmarks commonly encountered by agent
  engineers; demonstrate that each maps to a real model, harness, or evaluation
  decision; and test whether an explainer drives meaningful search traffic,
  experiment readership, or subscriptions.

## BL-007 — Cost efficiency & productivity coverage lens

- **Status:** ready (one-pager:
  `docs/ideas/cost-efficiency-productivity-topic.md`)
- **Priority:** medium
- **Outcome:** Readers who own the "does this agent pay for itself, and how do
  I make it cheaper per task" job find llm-digest.com covering it as a
  first-class theme — measurement and proof, not just cost reduction.
- **Scope:**
  1. One new wiki obstacle page (`proving-agent-roi`) in the existing `cost`
     area, written by the `wiki-curator` routine through the normal ingest
     path.
  2. Playbook selection guidance favoring cards with a measured cost or time
     delta.
  3. Later, if engagement proves out: a Foundations concept page and a
     precise multi-word `topical_bias` keyword micro-tune (separate,
     deliberate change).
- **Dependencies:** Wiki-curator routine capacity; enough source flow on the
  measurement/ROI angle to keep a page fresh; CTR and topic-page-view signals
  to validate interest.
- **Guardrails:** No loose "productivity" ranking keyword. The existing
  anti-hype filters (`hype_keywords`, `off_topic.policy_economics_governance`)
  stay untouched — enterprise AI-ROI marketing, vendor case studies, and
  macro-productivity content remain out of scope. No new wiki area, nav
  entry, or page type.
- **Promotion criteria:** `/topic/agent-cost` engagement vs. other wiki nodes
  supports the theme; the curator can source non-marketing evidence for the
  measurement angle at a 2–3 week refresh cadence; expected effect is framed
  against weekly returning readers.
