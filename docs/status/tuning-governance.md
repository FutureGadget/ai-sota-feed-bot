# Tuning Governance (v2)

Use this to avoid overfitting one run/day.

## Change order (least risky -> most risky)
1. Slot mapping (`slots.*.sources`)
2. Slot min/max caps
3. Candidate pool cap / LLM budget
4. Source bias
5. Topical bias
6. Top-band constraints

## One-change rule
- Change one logical group at a time.
- Run at least 2-3 full cycles before another major tweak.

## Guardrails
- Keep `max_per_source` constraints in slots.
- Keep `vendor_general_updates` low priority unless explicitly needed.
- Prefer slot changes over aggressive bias swings.

## Minimum validation checklist
- `run_full.sh` reaches `FULL_RUN_OK`
- Check `v2_stats` line for:
  - `prefilter` spread
  - `llm_used` within budget
  - slot selected counts
  - merge/top-band diagnostics
- Confirm no obvious duplicate URLs in final output.
- Verify target-source visibility (OpenAI/Anthropic/practitioner) in final top section.

## Rollback strategy
- Revert to last known good commit on main
- Or switch to preset baseline and remove local overrides

## Presets
- Baseline profile: `config/presets/balanced.yaml`
- `config/ranking_v2.yaml` should only carry active overrides + `preset` name.
