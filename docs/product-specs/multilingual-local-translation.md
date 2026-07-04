# Seamless local translation

LLM Digest should support non-English readers without turning multilingual
support into a recurring translation bill or a content-production workflow. The
first version is a **reader-local progressive enhancement**: the site remains
English at rest, and eligible browsers can translate the page's editorial
content on demand using browser-provided on-device translation.

The feature must feel like a native reading affordance, not an experimental AI
demo. If support is missing, slow, or unreliable, the page should quietly remain
English and the reader can still use the browser's built-in page translation.

## Goals

- Make non-English reading easier with near-zero server cost.
- Keep the site canonical, indexed, and stored in English.
- Add one shared browser module instead of page-specific translation forks.
- Preserve the product's technical precision: model names, source names, code
  terms, acronyms, URLs, and dates should not be mangled.
- Fail closed: unsupported browsers should not expose a broken translation UI.

## Non-goals

- Server-side translated pages.
- Per-language static builds, hreflang alternates, or translated RSS.
- User accounts, server-side language preference, or translation analytics that
  stores translated text.
- Bundling a custom WASM translation model in v1.
- Full UI localization. The first version translates the reading content, not
  every navigation label.

## Product behavior

### Entry point

The shared module adds one compact translation control in the existing page
chrome/context area when all of these are true:

- The document language is English.
- The browser supports a local translation provider.
- The reader's preferred language is confidently non-English.
- The current surface has registered translatable content.

The default label is language-specific, for example `Translate to Korean`. The
control appears near existing page controls: feed toolbar on `/`, archive/context
controls on recaps/playbook/storylines, and the generated page context row for
detail pages. It should not render as a modal, banner, or first-visit prompt.

### Interaction

1. Reader taps `Translate to <language>`.
2. The control switches to an inline progress state.
3. Text updates in place as each block is translated.
4. The control becomes `Show original`.
5. Reopening the same page uses the local cache and should feel instant.

The page must remain scroll-stable. Translation should not insert a large panel
above the reader's current position. If text expansion changes card heights,
that is acceptable; shifting the whole page with a banner is not.

### Fallbacks

- If no local provider is available, render no control by default.
- If a reader explicitly opens a future language menu and the browser cannot
  translate, show a small non-blocking message: `Use your browser's translate
  feature for this page.`
- If translation fails mid-page, keep successfully translated blocks, mark the
  control as retryable, and never delete the original text.
- If storage is unavailable, translation still works for the current page but
  is not cached.

### Autotranslation policy

Do not auto-translate in v1. Technical news loses trust when a page changes
language without the reader asking. Autotranslation can be reconsidered only
after explicit user preference exists and quality has been validated.

Exception: a URL that explicitly carries a supported target language is treated
as the reader's action:

```text
/story/<sid>?lang=ko
/daily/2026-07-03?lang=ja
/subscribe?lang=ko
/s?u=<encoded-source-url>&lang=zh-CN
```

When `lang` is one of `ko`, `ja`, or `zh-CN`, the shared module selects that
target language and starts the existing page translation flow after the page
registers translatable content. If in-page translation is unavailable, the same
URL opens the browser-assist instruction for that language. Unsupported language
codes are ignored. Share controls should preserve the active `lang` parameter so
a reader can share the same translated reading state without creating a separate
canonical page.

## Architecture

Add one shared client module:

```text
web/local-translate.js
```

It follows the same pattern as `web/nav-updates.js`:

- Loaded with `defer` by hand-authored shells and by
  `pipeline/render_static_pages.py`.
- Defensive no-op when required browser APIs or page hooks are absent.
- Owns feature detection, provider selection, glossary protection, translation,
  local caching, UI state, and telemetry events.
- Exposes a small debug/integration surface on `window.llmDigestTranslate`.
- Does not fetch server data and does not mutate feed/story API contracts.

Static page generation should define one asset tag constant, for example:

```python
LOCAL_TRANSLATE_ASSET_VERSION = "20260704-local-translate"
LOCAL_TRANSLATE_TAG = (
    f'<script src="/local-translate.js?v={LOCAL_TRANSLATE_ASSET_VERSION}" defer></script>'
)
```

Hand-authored shells use the same version string. A site-chrome contract test
should enforce this, matching the existing `nav-updates.js` and
`posthog-client.js` pattern.

## Provider contract

`local-translate.js` should route through a provider adapter interface so the
feature can start with browser-native translation and later add alternatives
without changing page code.

```js
/**
 * @typedef {Object} TranslationProvider
 * @property {string} id
 * @property {(source: string, target: string) => Promise<"available"|"downloadable"|"unsupported">} availability
 * @property {(source: string, target: string, hooks?: ProviderHooks) => Promise<TranslatorSession>} create
 */

/**
 * @typedef {Object} TranslatorSession
 * @property {(text: string) => Promise<string>} translate
 * @property {() => void} destroy
 */
```

Initial provider:

- `chrome-translator`: uses the browser `Translator` API when available.

Future provider, deliberately not v1:

- `transformers-wasm`: optional experiment using Transformers.js / ONNX Runtime
  with quantized models, gated behind manual opt-in and a size/performance
  review.

Provider selection is additive. Page code should never call `Translator`
directly.

## DOM integration contract

The module discovers content through semantic markers, not page-specific DOM
knowledge. Pages may opt in at section or block level:

```html
<main data-local-translate-surface="daily">
  <h1 data-translate-block>AI Daily Recap</h1>
  <section data-translate-block>
    ...
  </section>
</main>
```

Allowed attributes:

| Attribute | Meaning |
|---|---|
| `data-local-translate-surface` | Stable surface id: `feed`, `daily`, `weekly`, `story`, `storylines`, `playbook`, `map`, `foundations`, `voices`, `subscribe` |
| `data-translate-block` | Translate this element's human-readable text descendants as one logical block |
| `data-translate-skip` | Never translate this element or its descendants |
| `data-translate-term` | Preserve the exact text inside this element |
| `data-translate-ui-slot` | Preferred insertion point for the compact control |

The module should also include conservative defaults for existing page
structures so v1 does not require annotating every story card at once. Defaults
must be shallow and easy to remove after explicit markers are added.

Dynamic shells that fetch their reader content after page load, such as
`/playbook`, must call `window.llmDigestTranslate.scan()` after rendering a new
edition so the shared control and block cache bind to the current DOM instead
of the initial loading state.

Elements skipped by default:

- `code`, `pre`, `kbd`, `samp`
- `time`
- `a[href]` URL text when it is the visible URL
- source labels, domain names, metric badges, and archive controls
- nav/header/footer chrome
- buttons and form controls, except the translation control itself

## Glossary protection

Before sending text to a provider, the module replaces protected terms with
stable placeholders and restores them afterward. This is required for technical
trust.

Protected by rule:

- All-caps acronyms of 2-8 characters: `RAG`, `MCP`, `GPU`, `SWE`.
- Version/model patterns: `GPT-5`, `Claude Fable 5`, `Llama 4`, `Qwen3`.
- Code-like tokens: snake_case, kebab-case, dotted identifiers, package names.
- URLs, domains, emails, prices, percentages, and dates.
- Inline `data-translate-term` spans.

Maintain a small curated list in the module for high-value product terms:

```js
[
  "tool calling",
  "function calling",
  "retrieval-augmented generation",
  "RAG",
  "MCP",
  "evals",
  "inference",
  "latency",
  "context window",
  "context compaction",
  "agent orchestration",
  "LLM-as-judge"
]
```

The glossary is not a localization dictionary. It is a preservation list to
avoid worse-than-English technical output.

## Cache and state

Use local browser storage only.

| Key | Stores |
|---|---|
| `llm_digest_translate_pref_v1` | Reader's last chosen target language and provider id |
| `llm_digest_translate_cache_v1` | Small LRU cache of translated block text keyed by content hash and target language |
| `llm_digest_translate_seen_prompt_v1` | Whether the reader has seen the translation affordance |

Cache key:

```text
sha256(surface + canonicalPath + targetLanguage + normalizedSourceText)
```

Cache limits:

- Maximum 100 translated blocks.
- Maximum 1 MB serialized storage.
- Evict least recently used entries.

Never cache provider errors. Never store translated text server-side.

## Public browser surface

Expose a small object for page-level coordination and debugging:

```js
window.llmDigestTranslate = {
  available: boolean,
  provider: string | null,
  targetLanguage: string | null,
  state: "idle" | "checking" | "ready" | "translating" | "translated" | "error",
  translate(targetLanguage?: string): Promise<void>,
  showOriginal(): void,
  destroy(): void
}
```

This is not an API for third-party consumers. It is a local integration surface
for tests and for future page-specific controls.

## Accessibility

- Use a real `<button>`.
- Announce progress through `aria-live="polite"` on the control text.
- Do not steal focus when translation starts or completes.
- `Show original` must be keyboard reachable and visible.
- Respect `prefers-reduced-motion`; no animated typewriter or streaming text
  effect.
- Keep translated blocks' original semantics and headings.

## Telemetry

Use the existing optional `window.aiFeedPostHog.capture()` queue. No event
should include source text or translated text.

Events:

| Event | Properties |
|---|---|
| `translate_control_view` | `surface`, `provider`, `target_language`, `availability` |
| `translate_start` | `surface`, `provider`, `target_language`, `block_count`, `cache_hits` |
| `translate_complete` | `surface`, `provider`, `target_language`, `block_count`, `duration_ms`, `cache_hits` |
| `translate_error` | `surface`, `provider`, `target_language`, `phase`, `error_code` |
| `translate_show_original` | `surface`, `target_language` |

## Rollout plan

1. **Spec and contract tests.** Add this spec and tests that enforce one shared
   script tag across shells and generated pages.
2. **Skeleton module.** Add `web/local-translate.js` as a no-op feature detector
   with `window.llmDigestTranslate` and no visible UI unless support exists.
3. **Generated/static integration.** Load the shared script from
   `render_static_pages.py` and the hand-authored shells.
4. **First surfaces.** Enable explicit content markers on `/daily`, `/weekly`,
   and `/story/<sid>` first. These are the highest-value reading surfaces and
   are less DOM-heavy than the live feed.
5. **Feed and knowledge surfaces.** Add feed card, storyline, Playbook, map, and
   Foundations markers after the first surfaces pass visual QA.
6. **Quality review.** Test Korean, Japanese, Spanish, and Portuguese on recent
   pages with real technical terms; adjust glossary protection before widening.

## Validation

- Unit/static tests:
  - every relevant shell and generated page includes the shared script tag;
  - no page embeds a private translation fork;
  - `local-translate.js` contains provider abstraction, glossary protection,
    skip selectors, storage guards, and the public integration object.
- Browser tests:
  - unsupported browser renders no control and no console errors;
  - supported browser shows one compact control only when content exists;
  - translation preserves links, code, source labels, dates, and model names;
  - `Show original` restores the exact original text;
  - cached reload does not re-run translation for unchanged blocks;
  - mobile layout has no horizontal overflow.
- Manual QA:
  - Korean and Japanese technical text remains understandable;
  - page remains useful when translation is partial or fails;
  - no modal or banner interrupts first read.

## Rollback

Remove the shared script tag or make `local-translate.js` return before UI
creation. Because the feature is reader-local and does not alter data artifacts,
APIs, routing, or canonical HTML content, rollback is a static asset change.

## References

- Chrome built-in Translator API:
  `https://developer.chrome.com/docs/ai/translator-api`
- Transformers.js browser/WASM/WebGPU runtime:
  `https://huggingface.co/docs/transformers.js/en/index`
- Firefox local website translation:
  `https://support.mozilla.org/en-US/kb/website-translation`
