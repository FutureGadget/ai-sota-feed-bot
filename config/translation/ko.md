Write natural Korean for engineers, not machine-translated Korean. This guide applies to feed cards and static pages.

## Meaning
- Translate meaning, not words. Restructure sentences so they read naturally in Korean. Keep the source's facts, numbers, and claims exactly. Do not add, drop, or merge anything, and do not add commentary.
- Split an English sentence that chains three or more clauses into two Korean sentences instead of linking them with -고 or -며.

## Register
- Concise news style ending in -다 (for example "공개했다", "줄였다"), the same register as the daily and weekly recaps.
- No -습니다 and no -요, and never a mix of 입니다 and -다 in one text.
- First-person source text ("Hi HN, I'm building ...", "We're excited to announce ...") stays in the same -다 register and reports what the author says: "저자는 ...를 만들고 있다고 밝혔다", "...를 공개한다고 발표했다". Never write it as the author speaking to the reader.
- A boilerplate call to action ("Learn more.", "Read more", "Try it today") becomes "자세한 내용은 원문 참고.". Never use an imperative or propositive ending (알아보세요, 알아보자, 확인해 보세요).
- A heading or title may end in a noun phrase or in -다.

## Names and identifiers
- Keep product, model, company, library, benchmark, and paper names in their original form.
- Keep code identifiers, versions, flags, and file names in their original form.
- Write acronyms as is (MCP, RAG, KV, TTFT, CI, GPU).
- A title or heading is translated, with the names inside it kept. Leave it in English only when the whole title is itself a product, repository, or paper name.

## Numbers
- Keep every number, unit, percentage, and date exact. Korean number style is fine when the value is unchanged ("$1.2M" becomes "120만 달러", "35,000 items" becomes "35,000개").

## Terms
- Common nouns are ordinary lowercase Korean words: token is 토큰, never "Token". "Agentic" is 에이전틱 (or 에이전트 before a noun, as in "에이전트 워크플로"), the same way every time, never left in English.
- Use one Korean rendering per term across everything you translate. Prefer the term Korean engineers use: 에이전트, 추론, 서빙, 샌드박스, 벤치마크, 평가(eval), 프롬프트 인젝션, 컨트롤 플레인, 가중치, 컨텍스트 윈도우, 레이턴시.

## Markup
- A field can contain HTML. Keep every tag, attribute, URL, and entity exactly as written and translate only the text between the tags.
