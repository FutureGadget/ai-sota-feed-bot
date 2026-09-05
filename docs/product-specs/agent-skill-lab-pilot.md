# Agent Skill Lab pilot

## Product decision

Run Agent Skill Lab as a three-result editorial pilot inside the Agent Builder's
Playbook. The Lab gets durable nested URLs and a small publishing contract, but
it does not get a top-level navigation destination during the pilot.

The visible launch artifact is edition zero: a protocol that explains what the
Lab will hold constant, which three conditions it will compare, what it will
measure, and what evidence must exist before a verdict can be published. It is
not presented as an experiment result.

## Reader job

An engineer should be able to answer two questions in about 60 seconds:

1. Did the full skill materially change how the agent worked or the quality of
   the finished task?
2. Is that change useful enough to adopt for a similar workflow?

The Lab compares observable execution evidence, not prompt prose. Each result
must expose the fixed task, environment, repeated runs, outcomes, trajectory
summaries, costs, artifacts, limitations, and a practical recommendation.

## Pilot hypothesis

A recurring, reproducible field test gives the site's narrow engineering
audience a stronger reason to return than another navigation or local-state
feature. It should also make the email subscription proposition more concrete:
get the next result when it is ready.

The north-star remains weekly returning readers. Edition views, completion,
artifact opens, and attributed subscription completions are leading signals,
not replacement success metrics.

## Pilot sequence

- Edition 0: publish the method and evidence bar. No result or winner.
- Edition 1: debugging skill on a bounded repository regression.
- Edition 2: test-driven-development skill on a stateful behavior change.
- Edition 3: context-engineering skill on an unfamiliar-repository task.

The exact public skill revision, repository fixture, task, model, harness, and
budget are pinned in each result record before its runs begin. A result can use
a different skill candidate only if the record explains the change and still
uses the shared three-condition contract.

## Shared experiment contract

Every result compares exactly these conditions:

1. `no-skill`: the task and normal harness instructions only.
2. `minimal-instructions`: the task plus a short checklist that captures the
   skill's main claim without copying the full skill.
3. `full-skill`: the complete, version-pinned skill.

Records keep that canonical order so every teaser, table, and receipt view can
be scanned from baseline to full intervention without client-side reordering.

Every condition has the same number of independent runs, with at least three
runs per condition. The model, reasoning effort, harness, permissions,
repository fixture and revision, timeout, token ceiling, and cost ceiling stay
constant.

Each published result records `method.skill` with the skill name, public source
URL, immutable revision, and lowercase SHA-256 content digest. The environment
records the exact reasoning effort. Minimal-instruction and full-skill
conditions publish distinct instruction artifacts and digests; the full-skill
digest must match the pinned skill digest. The no-skill condition cannot carry
an instruction artifact.

The authored record stores raw run observations. Success counts and medians are
derived by deterministic code so displayed aggregates cannot drift from the
runs.

Required measures are:

- task success against predeclared criteria;
- final quality score against a disclosed rubric;
- elapsed time, input and output tokens, and estimated cost;
- tool calls and human interventions;
- recovery events and unnecessary actions;
- a short observable trajectory summary for each run.

Artifacts may contain sanitized prompts, tool-call timelines, diffs, test
output, and scoring receipts. Same-origin evidence lives under
`web/lab-artifacts/<slug>/` and is served from `/lab-artifacts/<slug>/`.
External evidence must use credential-free HTTPS. Artifact URLs cannot contain
query strings or fragments. Same-origin evidence is limited to inert `.json`,
`.jsonl`, `.md`, and `.txt` files. Only files referenced by a validated record
are staged, and both public artifact paths receive a sandboxing Content Security
Policy plus `X-Content-Type-Options: nosniff`. Artifacts must not contain secrets,
private repository content, subscriber information, or hidden model reasoning.

## Data contract

Published Lab records live under `data/playbook/lab/<slug>.json`. Drafts live
under `data/playbook/lab/drafts/` and are never indexed or deployed.

Common fields:

```json
{
  "schema_version": 1,
  "kind": "agent-skill-lab",
  "id": "lab-protocol",
  "slug": "protocol",
  "pilot_edition": 0,
  "pilot_size": 3,
  "state": "protocol",
  "date": "2026-09-04",
  "generated_at": "2026-09-04T00:00:00Z",
  "featured_until": "2026-09-18",
  "title": "Agent skills need receipts",
  "question": "What changes when the same agent gets no skill, a short checklist, or the full skill?",
  "summary": "A concise statement of the test and its value.",
  "method": {},
  "limitations": []
}
```

`state: "protocol"` is valid only for edition zero and cannot contain verdict,
recommendation, result runs, or winner language. `state: "published"` is valid
only for result editions 1 through 3 and requires the complete run contract,
verdict, recommendation, representative artifacts, and limitations.

`featured_until` controls temporary homepage and email promotion. It does not
delete the durable record or hide the latest Lab item from Playbook.

The slugs `drafts`, `index`, `latest`, and `list` are reserved by the store and
API selectors and cannot identify an edition.

A deterministic builder validates every record before writing
`data/playbook/lab/index.json` and `latest.json`. Any invalid record prevents all
derived writes. Each index entry binds to its validated source bytes with a
SHA-256 digest. The API, weekly email selector, and Vercel build verify that
binding so a source edit cannot bypass validation through a stale index. IDs,
slugs, and pilot numbers must be unique, editions must be contiguous from the
protocol, and same-origin artifact URLs are limited to `/lab-artifacts/`. The
builder rejects a missing same-origin file and verifies local pinned-skill and
instruction SHA-256 digests. The Vercel build stages only referenced inert
artifacts at the deployment root and mirrored `/web/` path.

## Web behavior

### Playbook home

`/playbook` renders its normal latest edition immediately, then loads the latest
valid Lab record as an optional enhancement. A failed or missing Lab request
does not delay or alter the Playbook.

The Lab teaser sits after the Playbook hero and before the change records. It
uses the existing instrument visual language: hairline rules, an accent edge,
monospace labels, and no card shadow or new navigation pill.

An explicit historical Playbook date does not inject a newer Lab record.

### Durable detail

`/playbook/lab/<slug>` is the complete record. It inherits the Playbook
navigation identity and leads with either the protocol status or a 60-second
verdict. Published results show derived condition summaries, every recorded
efficiency and trajectory measure, collapsible per-run receipts including
failures, setup, artifact links, limitations, replication details, and a finite
end marker.

### Homepage promotion

The feed may show one Skill Lab Editor's Desk insert after at least four ranked
stories when all of the following are true:

- the reader is in the default Brief view with no search;
- onboarding and the existing subscription nudge are already complete;
- the Lab record is inside its `featured_until` window;
- this Lab ID has not been opened or dismissed on this browser.

The insert consumes the existing maximum-two Editor's Desk budget. It never
adds a third promotional block or appears above the first story. Opening or
dismissing it retires that Lab ID's feed promotion. A successful detail render
from Playbook, email, or a direct link writes the same browser-local retirement
key. A restored feed page reconciles that key on `pageshow` so browser Back
cannot revive a stale promotion.

### Email promotion

The weekly email includes at most one unsent Lab record. A record becomes
eligible once its publication date is no later than the recap end and remains
eligible through `featured_until`, even if it was published just after the
previous Friday send. A small PII-free cursor records sent Lab IDs after a
successful broadcast so a record appears once. It links to the durable detail
URL with email attribution. Daily email is unchanged during the pilot.

## Measurement

PostHog receives no email address, prompt content, or artifact body. The pilot
uses these explicit events:

- `skill_lab_feature_view`: teaser became visible, with Lab ID, edition, and
  placement;
- `skill_lab_open`: a validated detail rendered, with `placement` set to
  `feed_insert`, `playbook_home`, `weekly_email`, or `direct`;
- `skill_lab_verdict_view`: result verdict became visible;
- `skill_lab_artifact_open`: artifact kind and condition only;
- `skill_lab_complete`: finite end marker became visible;
- `subscribe_success`: cadence plus allowlisted Lab attribution, never email.

The subscribe page rewrites its URL to the allowlisted attribution subset
before PostHog initializes, preventing arbitrary query values from entering the
automatic page-view URL. A honeypot 200 response presents the same neutral UI
to a bot but does not emit `subscribe_success` or mark the browser subscribed.

Existing anonymous identity and page views provide return cohorts. Analysis
compares next-week return and subscription completion for Lab readers against
the site's baseline, while treating the small pilot sample as directional.

## Accessibility and responsive requirements

- All interactive targets are at least 44 CSS pixels high on touch layouts.
- Condition labels and outcomes are explicit text, never color-only.
- Result tables have semantic headers and remain readable at 320 CSS pixels.
- Dynamic optional content is not placed inside the Playbook's `aria-live`
  region.
- Missing Lab data produces no empty frame, spinner, or error announcement.
- Reduced-motion preference disables optional movement.

## Non-goals

- A universal skill, model, or harness leaderboard.
- Automated model execution from the production website.
- A top-level Lab navigation destination during the pilot.
- Personalized experiment recommendations.
- Comments, accounts, voting, or community features.
- Publishing a winner from a single run or an incomplete evidence set.
- Translating Lab pages during this English-only pilot.

## Exit decision after edition 3

Continue or promote the Lab only if it proves both a repeatable editorial
method and a useful readership signal. Review weekly returning readers,
next-week return among Lab viewers, completion, artifact opens, attributed
subscriptions, production effort, and evidence-review failures.

If the signal is weak, stop publishing new editions and keep the four durable
records as an archive. If it is strong, design the permanent section, static
SEO rendering, retest policy, and operating cadence as a separate decision.

## Rollback

Remove the optional Playbook and feed renderers, the weekly email block, and the
Lab API selector. Existing Playbook editions and all other editorial surfaces
continue to work because the Lab store and UI are additive.
