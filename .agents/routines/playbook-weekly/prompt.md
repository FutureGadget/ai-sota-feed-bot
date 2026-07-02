# Weekly Agent Builder's Playbook

Read `.agents/routines/COMMON.md`,
`.agents/skills/playbook/SKILL.md`, and
`.agents/skills/writing-style/SKILL.md` completely, then execute the Playbook
routine with these requirements:

1. Build the input bundle with a seven-day lookback:

   ```bash
   python .agents/skills/playbook/scripts/build_playbook_input.py --days 7
   ```

2. Read the generated `date` and `already_published` result. If that edition
   already exists, stop successfully and report that it was already published.
   Do not overwrite it.
3. Read `data/playbook/input/latest.json` and curate a new
   `data/playbook/<date>.json` edition according to the Playbook skill. Select
   only actionable agent-engineering material; 4–8 strong cards are preferred.
4. Validate and rebuild the served indices:

   ```bash
   python .agents/skills/playbook/scripts/build_playbook_index.py
   ```

   Fix edition errors and repeat until validation succeeds.
5. Stage only `data/playbook/` and commit with:

   ```text
   playbook: edition <date>
   ```

6. Publish using the shared rebase-and-retry contract in `COMMON.md`.

Report the edition date, number of cards published, commit status, and push
status.
