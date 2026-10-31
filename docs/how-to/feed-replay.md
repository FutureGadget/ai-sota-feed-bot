# Replay the served Brief and read the scorecard

`scripts/feed_replay.py` answers three questions about the 24-hour Brief:

1. **Admission coverage:** how many of the day's judge keeps reached the served
   Brief, and why the rest did not.
2. **Stability:** across production run times, how much did the visible Brief
   change, and did any story leave before its 24-hour window expired?
3. **Mix:** what roles, sources and publish-to-admission lag does the pool hold?

It reads the committed `data/brief/*.json` ledgers, `data/quality/pool/*.json`
and `data/processed/runs_index.json`. It never calls the network and never
changes feed data.

## Run

```bash
python3 scripts/feed_replay.py
python3 scripts/feed_replay.py --days 7
python3 scripts/feed_replay.py --end 2026-10-31
python3 scripts/feed_replay.py --no-write
```

The report is written under
`data/quality/feed_benchmark/runs/<stamp>/report.{json,md}` (gitignored) unless
`--no-write` is set. The stdout log line is the daily/CI-friendly summary:

```text
feed_replay days=3 ledgers=3 runs=70 admitted=225 keeps=676 keeps_admitted=187
keeps_rate=0.2766 top10_jaccard_mean=0.8956 top10_jaccard_min=0.5385
rank_displacement_mean=0.3 unexpected_removals=0 expired_removals=126
```

`feed_day` lines follow with per-day admission, gate/quota rejections, prior
story skips, and median publish-to-admission lag.

## How to read it

- **`keeps_admission_rate`** is the share of the day's unique judge keeps that
  were served at the end of that day (the 24h window at 23:59 UTC). It is not
  meant to be 100%: the source/role quotas are flood guards. A low rate with
  high `source_quota` means the quotas bind; tune `config/brief.yaml`.
- **`unexpected_removals`** must be 0. A non-zero value means a story left the
  visible 24h window before its admission aged out. That is the bug Phase 1/2
  fixed; investigate the ledger writer or API merge if it moves.
- **`expired_removals`** is expected: items leave when their admission crosses
  24 hours.
- **`top10_jaccard_mean`** is how much the top of the Brief stays the same
  between refreshes. New stories entering the top is the freshness tradeoff,
  not churn; `min` is over pairs with at least 5 visible stories so cold starts
  do not dominate.
- **`rank_displacement_mean`** is the average absolute rank movement among
  stories present in both top-10 lists. Lower is calmer.
- **`published_lag_median_hours`** is the slow-source catch-up signal: how old
  the article was when the feed admitted it. A high median is expected for
  arXiv and slow RSS; a sudden drop is not a problem, but a sudden rise means
  the collector is falling behind.

## Tuning

The gates and quotas live in `config/brief.yaml`. The scorecard's `gate` and
`quota` counters show which one is binding. After changing quotas, rerun the
replay and compare `keeps_admission_rate`, `admitted`, and `top10_jaccard`.
Do not tune for a higher admission rate alone: the default Brief is meant to
stay finishable, and the over-cap pool is folded under "More from ...".

## Ops line

The daily `feed-ops-summary.yml` workflow runs `pipeline/ops_daily_summary.py`,
which now includes a `brief_ledger` block and a `brief_items`/`brief_gate`/
`brief_quota` tail on its `ops_summary` line. That is the quickest
daily check; use the replay when a number looks off.
