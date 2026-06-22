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
