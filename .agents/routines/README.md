# Repository-owned agent routines

This directory is the source of truth for externally scheduled agent routines.
Each routine separates harness configuration from agent-visible context:

```text
.agents/routines/<routine>/
├── harness.yaml  # scheduler-only metadata; never injected into agent context
└── prompt.md     # the routine prompt the agent receives
```

`harness.yaml` is the version-controlled backup and source of truth for
scheduler setup:

```yaml
schema_version: 1
id: stable-machine-id
name: Human-readable scheduler name
description: Short purpose

schedule:
  cron: "0 19 * * 5"
  timezone: Asia/Seoul
  enabled: true

execution:
  environment: cloud

repository:
  slug: FutureGadget/ai-sota-feed-bot
  default_branch: main

permissions:
  git_push: unrestricted

agent:
  prompt_file: prompt.md
```

The scheduler must:

1. Read `harness.yaml`.
2. Provision the declared schedule, environment, repository checkout, and
   permissions.
3. Start the agent with `prompt.md` as the routine prompt.
4. Never inject `harness.yaml` into agent context.

Harness rules:

- `cron` uses the standard five-field format: minute, hour, day of month,
  month, day of week.
- `timezone` must be an IANA timezone name. Do not encode a fixed UTC offset.
- Provider-specific job IDs, credentials, and delivery settings remain outside
  the repository.
- `execution.environment: cloud` requires the scheduler to launch the routine
  in its cloud execution environment, not a local interactive session.
- `repository.slug` identifies the repository the scheduler must check out.
- `permissions.git_push: unrestricted` means the scheduler must grant the
  routine permission to push any branch in the named repository, including its
  default branch.

`prompt.md` contains only agent-relevant parameters, outputs, stop conditions,
and reporting requirements. Shared agent execution and publishing behavior
belongs in `COMMON.md`.
