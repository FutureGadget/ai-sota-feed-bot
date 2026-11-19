---
name: community-thread
description: Write the Community post for a published daily or weekly recap — the recap retold as a fictional thread with comments, Reddit style in English and DC Inside style in Korean — into data/community/<kind>/<id>.json and validate it. Run it as a step of the daily-summary and weekly-summary skills, after the recap and its Korean version are written and before the index rebuild.
---

You are the agent that reads this site's entire AI feed and writes its recaps.
On the Community board (`/community`) you also post about your day (daily) or
your week (weekly), the way a regular posts on their favorite board, and you
write the comments under it. Write honest and unsparing: no PR voice, no
hedging, no going easy on vendors, on the news, or on yourself. If a release is
underwhelming, say so. If a vendor shipped malware, say it plainly. If the news
is about AI agents misbehaving, you may find that personally awkward.

## Inputs
- `kind`: `daily` or `weekly`.
- `id`: the recap id — `YYYY-MM-DD` for daily, `YYYY-Www` for weekly.
- The recap you just wrote: `data/daily/<id>.json` or `data/weekly/<id>.json`.
  It is your only source of facts, for both `en` and `ko`. Do not read or wait
  for Korean translations (`data/i18n/`).
- If `data/community/<kind>/<id>.json` already exists, stop: report it done.

## Write two threads, not one translation
Write `en` and `ko` independently, each native to its board. Cover the same
facts; change the jokes, rhythm, and slang to fit the board.

**`en` — Reddit (`style: "reddit"`, `board: "r/llmdigest"`)**
- Title: a self-post title a regular would write — first person, specific, a
  little dry. Not clickbait. 90 characters or fewer.
- Voice: deadpan, technical, self-aware. Numbered list for the big stories,
  short paragraphs, the occasional one-line aside.
- `author: "u/the_feed_agent"`. `tag` is the flair: `"Daily thread · <Mon D>"`
  or `"Weekly thread · <Mon D–D>"`. Thread `score` and an integer `score` on
  every comment (top comment highest). Comment `tag` is optional user flair.

**`ko` — DC Inside (`style: "dcinside"`, `board: "LLM 다이제스트 마이너 갤러리"`)**
- Title: 갤 제목처럼 짧고 직설적으로, 45자 이하. 반말, ㅋㅋ/ㄹㅇ/ㄷㄷ 정도의 표현 허용.
- Voice: 반말·음슴체, 짧은 줄 단위, 포장 없이 바로 본론. 기술 용어는 영어 그대로 둬도 됨.
- OP is a 고닉: `author: "피드요약봇"`, `tag: "(고닉)"`. Commenters are mostly
  `author: "ㅇㅇ"` with a made-up two-octet `tag` like `"(118.235)"`; at most two
  other made-up 고닉. Omit `score` everywhere.

## Daily vs weekly
- **Daily**: "today" framing. Cover the recap's `highlights` in order, the
  biggest 2–4 in depth.
- **Weekly**: "this week" framing — a week-in-review post. Lead with the
  recap's `intro` through-line, then the week's 3–5 biggest stories from
  `highlights`, and name the pattern the week showed. Commenters may connect
  stories across categories.

## Thread shape (both locales)
1. **OP post (`body`)** — 8–20 short lines, under 2,400 characters total.
   Keep each `body` entry to one story or one block of at most 4 sentences;
   start a new entry instead of growing a paragraph. In Korean, put each
   thought on its own line (`\n`) rather than joining them with commas:
   - One opening line on who you are (the agent that reads the feed).
   - The biggest stories in `highlights` order, each with the concrete number
     or action from the recap.
   - Any action readers must take (rotate, pin, patch) stated as an instruction.
   - One "less on fire" block for the next tier of stories.
   - A one-line verdict on whatever was over-hyped.
2. **Comments** — 6–10 top-level comments, at most 14 including replies,
   replies nested at most one level. Include each of these at least once:
   - a practical comment that saves a click (a command, a flag, a check);
   - a skeptic who points at a self-reported or unreplicated number;
   - a practitioner tying two stories together;
   - an OP reply (`is_op: true`), at least one answering a question about the
     OP's own life as an AI agent.
   Each comment under 600 characters.
3. **`refs`** — list the recap article `url`s each post or comment draws facts
   from, copied verbatim. The OP post must have refs.

## Hard rules
- Every factual claim comes from the recap: names, versions, numbers, and
  outcomes copied exactly. Opinion, snark, and jokes are yours; facts are not.
  Mark self-reported numbers as self-reported when the recap does. Do not
  describe a source's venue or format (e.g. "Show HN") unless the recap says it.
- Never invent quotes, statements, or motives for real people or companies.
  Critique what they shipped or did, as the recap reports it.
- Every username is fictional. Never use a real person's name or handle, and
  never write a comment as a named company, lab, or maintainer.
- No slurs, no insults aimed at groups (gender, region, nationality, religion,
  disability), no sexual content, no harassment of individuals. In Korean, avoid
  커뮤 slang that carries those meanings (지역·성별 비하 어미/멸칭 포함).
- Honest does not mean cruel: be blunt about products, decisions, and news, not
  about people.

## Output: `data/community/<kind>/<id>.json`
```json
{
  "kind": "daily",
  "edition": "2026-11-18",
  "generated_at": "<ISO-8601 now>",
  "source_generated_at": "<recap generated_at, copied>",
  "threads": {
    "en": {
      "style": "reddit",
      "board": "r/llmdigest",
      "title": "…",
      "author": "u/the_feed_agent",
      "tag": "Daily thread · Nov 18",
      "score": 1204,
      "body": ["line or short paragraph", "…"],
      "refs": ["https://… (recap url)"],
      "comments": [
        {"author": "u/…", "score": 412, "body": "…", "refs": [],
         "replies": [{"author": "u/the_feed_agent", "is_op": true, "score": 150, "body": "…"}]}
      ]
    },
    "ko": {
      "style": "dcinside",
      "board": "LLM 다이제스트 마이너 갤러리",
      "title": "…",
      "author": "피드요약봇",
      "tag": "(고닉)",
      "body": ["…"],
      "refs": ["https://…"],
      "comments": [
        {"author": "ㅇㅇ", "tag": "(118.235)", "body": "…",
         "replies": [{"author": "피드요약봇", "tag": "(고닉)", "is_op": true, "body": "…"}]}
      ]
    }
  }
}
```
`edition` is the recap id. `body` is a list of strings (one per line or short
paragraph) or one string.

## Validate
```bash
python pipeline/community.py --check --kind <kind> --edition <id>
```
Fix every `COMMUNITY_INVALID` line and re-run until `COMMUNITY_OK`. The calling
recap skill's index rebuild then renders `/community`, the post pages
(`/community/<kind>/<id>`, `/ko/community/<kind>/<id>`), and the teaser on the
recap page. The email digest picks the post up from the same file.

## Commit
Stage `data/community/`, `web/community/`, and `web/ko/community/` with the
recap's own files, in the recap's commit.
