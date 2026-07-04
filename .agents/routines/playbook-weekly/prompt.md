# Weekly Agent Builder's Playbook

Publish the Agent Builder's Playbook edition for llm-digest.com.

Before acting, read these contracts completely:

1. `.agents/routines/COMMON.md`
2. `.agents/skills/playbook/SKILL.md`
3. `.agents/skills/writing-style/SKILL.md`

## Run the routine

The Playbook skill owns the domain steps. Follow its routine in order, exactly
as written, with two overrides:

1. Build the input bundle with a seven-day lookback instead of the skill's
   default: `--days 7`.
2. Skip the skill's own commit/push step — publish using the shared
   rebase-and-retry contract in `COMMON.md` instead.

If the skill's dedup check finds the edition already published, stop
successfully and report that, without overwriting it.

## Publish

Stage only `data/playbook/` and commit with:

```text
playbook: edition <date>
```

Publish using the shared rebase-and-retry contract in `COMMON.md`.

Report the edition date, number of cards published, commit status, and push
status.
