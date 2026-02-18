---
name: personalization-boost-testing
description: Test and validate feed personalization boosting on Vercel + Turso for ai-sota-feed-bot. Use when toggling PERSONALIZATION_MODE, lowering thresholds for QA, verifying debug_personalization output, and checking click/impression effects in feed_events.
---

Run quick personalization QA safely and repeatedly.

## Preconditions
- Repo root: `ai-sota-feed-bot`
- `vercel` CLI authenticated and linked (`.vercel/project.json` exists)
- `turso` CLI authenticated

## Quick Test Flow
1. Set test env knobs on Vercel:
   - `PERSONALIZATION_MODE=active`
   - `PERSONALIZATION_MIN_CLICKS=1`
   - `PERSONALIZATION_MIN_IMPRESSIONS=20`
2. Deploy production once (`vercel --prod --yes`).
3. Query debug feed for anon user:
   - `/api/feed?...&anon_user_id=...&debug_personalization=1`
4. Confirm diagnostics:
   - `mode=active`
   - `applied=true`
   - boosts (`_source_boost`, `_topic_boost`, `_personal_boost`) are non-null.
5. Validate event ingestion by checking Turso `feed_events` counts and latest click/impression rows.

## Commands
- Run scripted QA:
  - `bash skills/personalization-boost-testing/scripts/run_personalization_smoke.sh <anon_user_id>`
- Manual feed debug:
  - `curl -sS 'https://ai-sota-feed-bot.vercel.app/api/feed?limit=10&anon_user_id=<id>&debug_personalization=1' | jq '.personalization, .items[0]'`
- Manual DB check:
  - `turso db shell ai-sota-feed-bot "select event_type,count(*) from feed_events group by 1;"`

## Cleanup (post-test)
After QA, optionally revert safer defaults:
- `PERSONALIZATION_MODE=shadow`
- `PERSONALIZATION_MIN_CLICKS=3`
- `PERSONALIZATION_MIN_IMPRESSIONS=30`
Then redeploy.
