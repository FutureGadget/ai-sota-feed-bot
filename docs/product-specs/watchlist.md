# Watchlist

Readers pick the tools, model families and topics they run. The site then
shows what changed for those since they last looked, and can email them on days
something changes.

## Why

Weekly returning readers stayed at 4-7 from 2026-08-31 to 2026-11-02 while new
readers grew from 3 to 89 a week (`data/metrics/weekly_returning_readers.json`).
People arrive, read two or more pages and do not come back. The only return
offer was the daily digest, a large commitment for a first visit, and storyline
Follow covers about a dozen threads. A watchlist gives a first-time reader a
small, specific reason to return: "tell me when Claude Code changes".

This is a layer the reader builds on top of the edition. The Brief, its order
and its ranking stay the same for everyone (BL-003 guardrail: no opaque
personalized ranking).

## Entities

`config/watch.yaml` is the curated list: slug, label, kind (`tool`, `model`,
`topic`), title `terms`, optional `not` phrases and `sources`.

A story is news about an entity when its **title** matches a term, or it comes
from one of the entity's sources. Summaries are not matched: a passing mention
is not news about the thing.

- `claude code` matches the words in order, as whole words.
- `qwen*` matches any word that starts with `qwen`.
- `not` phrases are removed before matching, so "Claude Code 2.1" is not news
  about Claude models.
- Pre-release builds of release-type stories (alpha, beta, rc, dev, nightly)
  are left out. They stay in the Releases tab.

Slugs are stored in browsers and in the email provider. Never rename or reuse
one. Deleting an entity retires it: browsers and the email job ignore unknown
slugs.

Adding an entity: edit `config/watch.yaml`, add a case to
`tests/fixtures/watch_match_cases.json`, run `python pipeline/watch.py build`,
and commit the two generated files.

## Data

`pipeline/watch.py build` runs in the hourly feed run after
`story_store.py sync`. It reads stories that entered the store in the last
`window_days` (30) and writes:

| File | Reader | Contents |
|---|---|---|
| `data/watch/index.json` | `publish/publish_follows.py` | per entity: count, `last_updated`, 12 newest stories with URLs |
| `web/watch-data.json` | `web/watchlist.js` | the matching rules and 5 newest stories per entity, no URLs |

"New" is measured by `first_seen`, when the story entered this site, not by
its publication date. Both files carry no build timestamp, so a run with no new
matching story leaves them unchanged.

The matching rules exist twice: `pipeline/watch.py` and `web/watchlist.js`.
`tests/fixtures/watch_match_cases.json` is run against both.

## Reader surfaces

**Story pages.** A story that matches at least one entity gets a Watch section
after "Continue reading", with one chip per entity. Stories that match nothing
get no section and do not load the script. After the first Watch tap the
section offers email alerts, because that tap is the moment of intent.

**Feed cards.** The same chips sit in the card's "⋯" panel under Share and
Hide. The card face is unchanged (`feed-front-page.md`).

**Feed module (`#watchHome`, above the Editor's Desk updates).**

| State | Shows |
|---|---|
| No watchlist | "Watch what you run", the busiest tools and models as chips (4 on a phone), "All N", and a dismiss button |
| Dismissed, no watchlist | Nothing. Chips remain on cards and story pages |
| Watching, something new | "N new", up to 6 rows (2 per entity, newest first), Mark seen, Edit |
| Watching, nothing new | One line: "Nothing new in N watched", Edit |

A story is new for an entity when it entered after the reader last marked that
entity seen, and within the last 7 days. The cap keeps a reader returning after
a month from facing a backlog.

English pages only. The Korean feed does not load the watchlist yet.

## Browser state

| localStorage key | Value |
|---|---|
| `ai_feed_watchlist_v1` | `{slug: {added_at, seen}}`, at most 25 |
| `ai_feed_watch_email_v1` | `{slugs, at}`: which topics this browser sent for email. The address is not stored |
| `ai_feed_watch_intro_dismissed_v1` | `"1"` once the prompt is dismissed |

## Email alerts

`POST /api/subscribe { action: "watch", email, slugs, hp?, reader_id? }`
(`lib/follow.js`) adds the slugs to the contact's `watched_topics` property and
puts the contact in the existing "Storyline followers" segment. It adds and
never replaces, so a second browser cannot wipe a list. It does not subscribe
anyone to the daily or weekly digest. It is an action on the existing
`/api/subscribe` route, so the Worker route table is unchanged.

When a reader adds topics after giving an email, the module says "Email alerts
cover 2 of 3" and offers Update, which asks for the address again.

`publish/publish_follows.py` sends the alerts in the same email as storyline
follows, after the daily digest:

- Cursor `data/email/state.json -> follows.watch_sent_through`. Its first run
  only sets it, so launch mails no backlog.
- One email per reader per run, so at most one a day. Up to 3 stories per
  topic, then "+N more". A story that matches two watched topics is listed
  once.
- Each topic has a signed "Stop watching" link (`&k=w`, token over
  `unfollow:<contact>:w:<slug>`). "Stop all" (`s=*`) clears stories and topics.
- `config/email.yaml -> follows.watchlist: false` turns the watchlist part off
  and leaves storyline alerts running.

## Measurement

PostHog events: `watch_home_view {state, watched, new_count}`,
`watch_toggle {slug, action, surface, total}`, `watch_item_click {slug}`,
`watch_mark_seen`, `watch_intro_dismiss`, `watch_email_view {surface}`,
`watch_email_success {surface, count}`.

Judge it by the north-star metric: weekly returning readers among browsers
with at least one `watch_toggle`, against those without. Secondary: the share
of story-page visitors who watch something, and watchers who add an email.

## Not in this version

- Korean feed and translated story pages.
- Watch chips on Model Radar rows and Agent Know-How topic pages.
- A page for managing the watchlist outside the feed module.
- Syncing a watchlist between browsers without email.
