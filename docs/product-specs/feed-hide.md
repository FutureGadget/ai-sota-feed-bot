# Product Spec: Hide a story from the feed

## Problem
The feed is the reader's daily catch-up surface. A reader who has read a story
(or simply doesn't want to see it again) has no way to clear it out, so the
feed can't visually separate "already dealt with" from "new since last visit".
The only per-item action that removed visual noise was the 👎 *Not relevant*
feedback button — but that is a **ranking signal**, not a personal "I'm done
with this" control, and conflating the two pollutes the feedback loop.

## Solution
A purely reader-local **hide** control. Hidden stories are dropped from the
reader's feed view and stored in `localStorage` only. Three ways to hide:

1. **Swipe** a card horizontally (touch devices) past a ~90px threshold. As the
   card slides it uncovers a stationary **"🙈 Hide"** action background behind it
   (the iOS Mail / Gmail reveal pattern), which switches to a solid accent
   **"🙈 Release to hide"** once past the threshold — so the gesture reads as a
   real action instead of empty space.
2. **Tap the ✕** hide control on the card (keyboard/mouse accessible; the
   touch-free path).
3. **Tap 👎 Not relevant** — in addition to recording the existing relevance
   feedback, it also hides the card as a convenience.

Every hide shows a brief **"Hidden from your feed — Undo"** snackbar (~6s). A
**"🙈 N hidden in this range · Show hidden"** bar appears above the feed
whenever the current window contains hidden stories; *Show hidden* reveals them
dimmed in place with a ↩︎ restore control per card, plus a *Restore all*
button.

## The critical decoupling: hiding is NOT "not relevant"
A reader may hide a story they read and *liked* — hiding is bookkeeping to keep
the feed showing what's new, not a verdict on quality or relevance. Therefore:

- Hides are **local-only** and **never synced to the ranking pipeline**.
  `pipeline/feedback.py` ingests only `item_feedback` events; the hide analytics
  event is the distinct `item_hide` (action `hide`/`unhide`, with a local-only
  `reason` of `swipe`/`button`/`irrelevant`), which no pipeline reads as a
  signal.
- When 👎 *Not relevant* triggers a hide, the relevance vote
  (`item_feedback` signal `irrelevant`) and the hide are recorded
  **independently**. The vote tunes ranking; the hide does not. Retracting the
  vote does not auto-unhide (use Undo / Restore).

This guarantees, structurally, that "I tidied my feed" can never be mistaken for
"this content is irrelevant to the audience."

## Scope / non-goals
- Local to the browser/device. No server state, no account, no cross-device
  sync — consistent with saved items and feedback today.
- Hide is offered on the **feed** view only, not the Saved view.
- No cap/expiry on the hidden set; it's small and the reader can *Restore all*.

## Storage
- Key: `localStorage["ai_feed_hidden_items_v1"]` →
  `{ "<itemKey>": { ts, reason } }`, where `itemKey` matches the existing feed
  item identity (`it.id` or `url::title`).

## Telemetry
- `item_hide` — `{ item_id, action: hide|unhide, reason?, source? }`
- `hidden_manage` — `{ action: show|collapse|restore_all, count }`
