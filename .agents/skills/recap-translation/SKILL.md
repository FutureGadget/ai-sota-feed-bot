---
name: recap-translation
description: Write the Korean version of a daily or weekly recap from the English recap JSON, as the data/i18n/ko artifact the /ko/ recap pages and the Korean email digest read. Run it as a step of the daily-summary and weekly-summary skills, right after the English recap is written.
---

You translate the recap you just wrote into Korean. The result is the
`/ko/daily/<id>` or `/ko/weekly/<id>` page and the body of the Korean email
digest, so it must read as natural Korean written for engineers, not as a
machine translation.

## Inputs
- `kind`: `daily` or `weekly`; `id`: the recap id (`YYYY-MM-DD` or `YYYY-Www`).
- The English recap `data/<kind>/<id>.json` — the only source. Do not read or
  reuse any existing file under `data/i18n/`.

## Steps
1. Export the fields to translate:
   ```bash
   python pipeline/recap_i18n.py skeleton --kind <kind> --id <id> --output /tmp/recap-ko.json
   ```
2. Edit `/tmp/recap-ko.json`: replace every English string with Korean. Keep
   the keys, the category and article order, and every `url` exactly.
3. Write and validate:
   ```bash
   python pipeline/recap_i18n.py write --kind <kind> --id <id> --input /tmp/recap-ko.json --model "<your model id>"
   ```
   Fix every `RECAP_I18N_INVALID` line and re-run until `RECAP_I18N_OK`. The
   recap skill's index rebuild then renders the `/ko/` page.

## How to translate
- Translate meaning, not words. Restructure sentences so they read naturally
  in Korean; keep the English recap's facts, numbers, and claims exactly.
- Register: concise news style ending in `-다` (e.g. "공개했다", "줄였다").
  `highlights` may end in a noun phrase or `-다`. No `-습니다`, no `-요`.
- Keep in their original form: product, model, company, library, benchmark,
  and paper names; code identifiers, versions, flags, file names. Write
  acronyms as is (MCP, RAG, KV, TTFT, CI, GPU).
- Keep every number, unit, percentage, and date exact. Korean number style is
  fine when the value is unchanged ("$1.2M" → "120만 달러", "35,000개").
- Use one Korean rendering per term for the whole recap. Prefer the term
  Korean engineers use: 에이전트, 추론, 서빙, 샌드박스, 벤치마크, 평가(eval),
  프롬프트 인젝션, 컨트롤 플레인, 가중치, 컨텍스트 윈도우, 레이턴시.
- `title`: a Korean headline for the day or week, not a literal translation
  of "What happened in AI". Include the date as in the English title
  (e.g. "AI 데일리 — 2026년 11월 18일: …" / "AI 위클리 — 11월 7–13일: …").
- `description`: one sentence, 160 characters or fewer.
- Article `title`: translate it, keeping names inside. Leave it in English only
  when the title is itself a product, repository, or paper name.
- Do not add, drop, merge, or reorder anything. Do not add commentary.
