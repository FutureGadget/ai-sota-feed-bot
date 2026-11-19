# Daily community thread

Status: experiment (2026-11-19).

The daily recap can carry a second telling of the same day: a fictional
community thread posted by the agent that writes the recap. English pages show
a Reddit-style thread (`r/llmdigest`); Korean pages show a DC Inside-style
gallery post (`LLM 다이제스트 마이너 갤러리`). The two are written separately for
each community, not translated.

## Behavior
- Source: `data/daily/thread/<date>.json`, written by
  `.agents/skills/daily-thread/` after the day's recap is published.
- `/daily/<date>` and `/daily` render `threads.en` below the categories, above
  the finish line. `/ko/daily/<date>` renders `threads.ko` when that Korean page
  exists. A locale without a thread renders nothing.
- The thread is a collapsible card (open by default): board, title, OP author
  and stats, the OP post, then comments with one level of replies. Each post
  lists its source articles in a collapsed "Sources" list.
- Every thread shows a fixed note that it is fictional, written by the editor
  agent, with made-up usernames and scores.

## Contract
- Facts come only from the recap. Every `refs` URL must be a recap article URL
  (`pipeline/recap_thread.py --check` enforces this, plus length, nesting, and
  comment-count caps).
- An invalid sidecar is skipped with a warning; the recap page still renders.
- The sidecar is not served by `/api/daily` and is not synced to R2
  (`r2_sync.py` uploads top-level `data/daily/*.json` only).

## Open questions
- Whether readers open, scroll, or share the thread (add a PostHog event before
  deciding to keep it).
- Whether to carry it into the email digest and the explainer video.
