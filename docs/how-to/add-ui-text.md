# Add UI text to the home page

Use this when you add or change a label, message, or sentence on the home page,
or when you add a language to it.

The home page has one source, `ui/templates/index.html`. The build
(`pipeline/render_home.py`) writes `web/index.html` and `web/<locale>/index.html`
from it. Every string a reader sees comes from `config/ui/<code>.json`, one file
per language in `config/locales.json`. A Korean page is the English page with
Korean text, so a feature added to the template reaches every language at once.

Never edit `web/index.html` or `web/ko/index.html` by hand. The build rewrites
them, and `tests/test_home_template.py` fails when a committed page is stale.

## How text reaches the page

| Where the text is shown | How you write it |
| --- | --- |
| HTML in the template | `{{t:key}}` |
| A string inside a JSON value in the template | `{{json:key}}` |
| A link to a page that may have a localized version | `{{href:/path}}` |
| Inline script | `t('key')` or `t('key', { name: value })` |
| Inline script, a sentence that holds trusted markup | `tHtml('key', { link: html })` |
| `web/site-chrome.js`, `nav-updates.js`, `subscribe-inline.js`, `watchlist.js`, `skills-strip.js` | `tr('key', 'English text', vars)` |

The build embeds a `window.UI` dictionary in each page. It holds only the keys
that page's scripts name in a quoted literal, so write the key out in full. Do
not build one with `'slot.' + name`. Pick between keys with a ternary or a
lookup table of literals instead.

The external scripts also run on pages that have no dictionary. `tr()` shows the
English text you pass when `t()` does not exist, so that text must equal the
English value in `config/ui/en.json`. A test checks this.

## Add a string

1. Choose a key shaped `area.name`, such as `card.englishTag`. Keys are flat.
   Write a plural as two keys, `area.nameOne` and `area.nameMany`, and pick one
   in code.
2. Add the key to `config/ui/en.json` and to every other `config/ui/<code>.json`.
   Keep each file sorted by key.
3. Use the key in the template or the script, as the table above shows.
4. Rebuild and commit the generated pages with the template and dictionaries.

   ```bash
   python3 pipeline/render_home.py
   ```

5. Run the guards.

   ```bash
   python3 -m pytest -q -p no:cacheprovider tests/test_ui_dictionary.py tests/test_home_template.py tests/test_home_languages.py
   ```

## Write the text

- Write plain text. The dictionary holds no markup. Put the tag in the template
  and pass trusted markup into `tHtml()` as a variable.
- Do not use a straight double quote. The text is embedded as JSON and as an HTML
  attribute. Use curly quotes.
- Write one whole sentence per key, with `{name}` placeholders for the parts that
  change. Do not join pieces in code, because word order differs by language.
- Escape in the caller. `t()` returns plain text, so wrap it in `esc()` when you
  put it in HTML.
- Keep product and model names, and source names, in English in every language.

For Korean, reuse the wording the site already uses before you write new text.
Check `config/translation/ko.md` for terms, and the Korean recap, community, and
email copy for phrasing. A new string should be short and natural. The home page
uses the polite register ("-습니다", "-세요").

## Link to a page that may not exist in another language

Wrap the path in `localHref('/daily')` in a script, or `{{href:/daily}}` in the
template. It returns the localized path only when that page exists, and the
English path otherwise. A link to a localized page that does not exist is a 404
with no fallback, because the Worker has no English fallback for `/ko/...`.

The pages that have a localized version are listed in `LOCALIZED_PAGES` in
`pipeline/render_home.py`, plus every `web/<locale>/storyline/<slug>.html`.
Add a path there only when the file exists and the Worker routes it
(`STATIC_REWRITES` in `worker/src/index.js`).

## What the tests check

`tests/test_ui_dictionary.py` fails when:

- a key the template or a script names is missing from any language;
- a language has a key `en.json` lacks, or drops a placeholder;
- a script builds a key from pieces;
- key-shaped text in a script is not in the dictionary, which a typo causes;
- a key is unused;
- a `tr()` fallback differs from `en.json`;
- text outside script and style in the template is not a dictionary token. The
  only exceptions are the product name and the file format name in
  `STATIC_TEXT_ALLOWLIST`, key names inside `<kbd>`, and text with no letters.

`tests/test_home_template.py` fails when a committed page differs from the build.
`tests/test_home_languages.py` and `tests/test_home_language_runtime.mjs` check
the language declarations, that every language has the same sections, and that
every localized link reaches a page that exists.

## Add a language

1. Add the language to `config/locales.json`. Set `path_prefix`, `label`, and the
   `dates` patterns.
2. Copy `config/ui/en.json` to `config/ui/<code>.json` and translate every value.
3. Add the localized pages the home page links to (see `LOCALIZED_PAGES`), and a
   `STATIC_REWRITES` route for `/<prefix>/`.
4. Run `python3 pipeline/render_home.py`. The build writes
   `web/<prefix>/index.html` and fails if a key is missing.
5. Run the guards above.

## Related

- `docs/product-specs/localized-live-feed.md` for how the localized home page and
  its feed behave.
- `docs/how-to/add-pretranslated-pages.md` for localized static pages.
