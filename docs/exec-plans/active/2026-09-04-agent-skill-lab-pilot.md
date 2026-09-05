# Agent Skill Lab pilot execution plan

## Status

Implementation complete and verified as of 2026-09-05. Edition zero publishes
only the protocol. Running the three result experiments still requires explicit
owner approval of the task fixtures, time, and model-cost budget.

Approved direction: a three-result, email-first pilot incubated inside Playbook,
with an honest edition-zero protocol and no top-level navigation destination.

Product contract:
`docs/product-specs/agent-skill-lab-pilot.md`.

## Outcome

- Publish a visible protocol without implying that experiment runs occurred.
- Provide a versioned, deterministic contract for three result editions.
- Keep the latest Lab discoverable when normal Playbook editions advance.
- Give every result a durable nested URL and finishable evidence layout.
- Promote current Lab records through the existing bounded feed and weekly
  email surfaces.
- Attribute views, completion, artifact opens, and signup success without PII.

## Implementation slices

### Slice 1: contract and publication safety

Files:

- `pipeline/build_skill_lab.py`
- `tests/test_skill_lab_contract.py`
- `data/playbook/lab/protocol.json`

Acceptance:

- [x] Protocol and result variants validate against schema version 1.
- [x] Result editions require three conditions and repeated raw runs.
- [x] Displayed aggregates can be derived from raw runs.
- [x] Drafts are ignored and invalid input causes no derived writes.
- [x] The builder writes deterministic `index.json` and `latest.json`.
- [x] Same-origin evidence is confined to `/lab-artifacts/`, exists before
      publication, and matches pinned digests where one is declared.

### Slice 2: additive API selector

Files:

- `api/playbook.js`
- `tests/test_playbook_api.mjs`
- `vercel.json`
- `.vercelignore`

Acceptance:

- [x] `?lab=latest`, `?lab=list`, and `?lab=<slug>` have stable response shapes.
- [x] Invalid slugs cannot become filesystem paths.
- [x] Missing and malformed data fail with bounded public errors.
- [x] Drafts are excluded from deployment.
- [x] Existing latest, date, list, source-index, and locale behavior is intact.

### Slice 3: Playbook teaser

Files:

- `web/playbook.html`
- `tests/test_playbook_surface.py`

Acceptance:

- [x] The normal edition renders without waiting for Lab data.
- [x] The latest Lab appears between the hero and change records on `/playbook`.
- [x] Historical Playbook dates do not receive cross-date Lab content.
- [x] Missing or failed Lab data leaves no visual residue.
- [x] View and open events carry only bounded metadata.

### Slice 4: durable Lab detail

Files:

- `web/playbook-lab.html`
- `tests/test_skill_lab_surface.py`
- `vercel.json`

Acceptance:

- [x] `/playbook/lab/<slug>` inherits the Playbook navigation identity.
- [x] Protocol and published-result states have distinct, honest hierarchy.
- [x] Success counts and medians are calculated from run records.
- [x] Aggregate tables and collapsible receipts expose every required run
      metric, failure, and trajectory summary.
- [x] Artifact URLs are allowlisted again at the rendering boundary.
- [x] Detail view, verdict, artifact, completion, and subscribe actions are
      measured without prompt bodies or PII.

### Slice 5: bounded feed promotion

Files:

- `web/index.html`
- `tests/test_live_feed_surface.py`

Acceptance:

- [x] Lab loading is fail-soft and does not gate feed paint.
- [x] Promotion appears only in the default Brief context and freshness window.
- [x] First-visit onboarding and the existing subscribe nudge win.
- [x] The existing Editor's Desk cap remains two.
- [x] Open or dismiss retires only that Lab ID.

### Slice 6: weekly email promotion

Files:

- `publish/publish_email.py`
- `tests/test_publish_email.py`

Acceptance:

- [x] The newest eligible unsent Lab record carries into one weekly send until
      its `featured_until` expiry, then advances the bounded Lab cursor.
- [x] Weekly selection fails closed unless the complete protocol-first store,
      derived snapshots, source digests, and local evidence all validate.
- [x] The link carries bounded email and Lab attribution.
- [x] Daily email and no-Lab weekly output are unchanged.
- [x] Dry-run and secrets-gated no-op behavior remain intact.

### Slice 7: signup attribution

Files:

- `web/subscribe.html`
- `tests/test_subscribe_surface.py`

Acceptance:

- [x] A successful first-party signup emits `subscribe_success`.
- [x] Only cadence, allowlisted referrer, and bounded Lab ID are captured.
- [x] The email address never enters analytics properties.
- [x] Invalid query attribution is removed before automatic page-view capture.
- [x] Honeypot 200 responses do not emit a conversion or mark local state.

### Slice 8: operating documentation

Files:

- `docs/product-specs/index.md`
- `docs/generated/db-schema.md`
- `docs/design-docs/decision-log.md`
- `AGENTS.md`

Acceptance:

- [x] Data, API, UI, email, measurement, and rollback contracts are indexed.
- [x] BL-004 points to this pilot and no longer says `needs-spec`.
- [x] Repository context lists the Lab store and route.

## Verification

Verified with 485 Python tests, 67 Node tests, focused publication checks,
Python and JavaScript syntax checks, and `git diff --check`. The pilot adds no
package dependency. A read-only `npm audit` also found pre-existing vulnerable
transitive packages in the repository lockfile; remediation is separate from
this dependency-free pilot.

Real-browser verification covered 320, 768, 1024, and 1440 CSS pixels in light
and dark themes. It confirmed no horizontal overflow, 44-pixel Lab actions,
semantic heading order, the honest protocol state, feed placement after five
stories, dismissal without losing story cards, and successful attributed
signup. A synthetic, non-published result fixture also verified the aggregate
tables and expanded run receipts at 320 and 768 CSS pixels in light and dark
themes, with no page overflow and touch controls above 44 pixels. Automated
surface tests cover result-state and optional-error behavior.

## Stop conditions

- Do not create result data without actual repeated runs and reviewed artifacts.
- Do not run a large agent swarm or experiment harness without explicit owner
  approval of the time and model-cost tradeoff.
- Do not deploy, merge, or email subscribers as part of this implementation.
- Do not add a top-level navigation item during the pilot.
