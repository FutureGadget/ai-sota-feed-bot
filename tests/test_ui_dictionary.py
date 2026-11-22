"""Guards for the UI dictionary (config/ui/<code>.json).

Every language's home page is built from one template, so text that skips the
dictionary shows up in English on a Korean page, and a key one language lacks
breaks that language's build or shows the key itself. These tests fail before
either reaches a reader. See docs/how-to/add-ui-text.md.
"""

from __future__ import annotations

import ast
import re
import unittest
from html.parser import HTMLParser

from pipeline import locales, render_home

ROOT = render_home.ROOT
DEFAULT = locales.DEFAULT
TEMPLATE = render_home.TEMPLATE_PATH.read_text(encoding="utf-8")
EXTERNAL_SCRIPTS = ("site-chrome", "nav-updates", "subscribe-inline", "watchlist", "skills-strip")
PLACEHOLDER = re.compile(r"\{(\w+)\}")

# Template text that is not translated on purpose: a product name and a file
# format. Key names in <kbd>, numbers, and symbols are skipped as well. Anything
# else must come from the dictionary.
STATIC_TEXT_ALLOWLIST = frozenset({"LLM Digest", "RSS"})

# Attributes that hold text a reader sees or a screen reader speaks.
TEXT_ATTRIBUTES = ("title", "aria-label", "placeholder", "alt")
META_TEXT = {("name", "description"), ("property", "og:title"), ("property", "og:description"), ("name", "twitter:title"), ("name", "twitter:description")}


def script_sources() -> dict[str, str]:
    sources = {"ui/templates/index.html": TEMPLATE}
    for name in EXTERNAL_SCRIPTS:
        sources[f"web/{name}.js"] = (ROOT / "web" / f"{name}.js").read_text(encoding="utf-8")
    return sources


_CALL = re.compile(r"(?<![\w.$])(?:t|tHtml|tr)\(")
_LITERAL = re.compile(r"""(['"`])([A-Za-z]\w*(?:\.\w+)+)\1""")


def first_arguments(text: str) -> list[tuple[int, str]]:
    """(line, source) of the first argument of every t(), tHtml() and tr() call."""
    found = []
    for match in _CALL.finditer(text):
        if text[: match.start()].rstrip().endswith("function"):
            continue
        depth, quote, i = 0, "", match.end()
        start = i
        while i < len(text):
            ch = text[i]
            if quote:
                if ch == "\\":
                    i += 1
                elif ch == quote:
                    quote = ""
            elif ch in "'\"`":
                quote = ch
            elif ch in "([{":
                depth += 1
            elif ch in ")]}":
                if depth == 0:
                    break
                depth -= 1
            elif ch == "," and depth == 0:
                break
            i += 1
        argument = text[start:i].strip()
        if argument:  # an empty t() is prose in a comment
            found.append((text.count("\n", 0, match.start()) + 1, argument))
    return found


def builds_a_key(argument: str) -> bool:
    """True when a first argument glues a key together from pieces, such as ``'slot.' + name``.

    A bare name or ``map[name]`` is fine: the literal keys are written out where
    they are chosen. A literal, or a ternary of literals, is fine too.
    """
    if not re.search(r"""['"`]""", argument):
        return False
    pieces = [argument]
    if "?" in argument:
        pieces = [part.strip() for part in argument.partition("?")[2].split(":")]
    return not all(re.fullmatch(r"""(['"])[\w.]+\1""", piece) for piece in pieces)


def literal_keys(text: str) -> set[str]:
    """Every key-shaped string literal in a script, the way the build finds the keys a page needs."""
    return {m.group(2) for m in _LITERAL.finditer(text)}


def tokens(text: str) -> set[str]:
    return set(re.findall(r"\{\{(?:t|json):([^{}]+)\}\}", text))


class DictionaryShapeTest(unittest.TestCase):
    def test_every_language_has_every_key_of_the_default(self) -> None:
        default = set(locales.ui(DEFAULT))
        for code in locales.others(DEFAULT):
            with self.subTest(code=code):
                self.assertEqual(sorted(default - set(locales.ui(code))), [], f"config/ui/{code}.json lacks these keys")

    def test_no_language_has_a_key_the_default_lacks(self) -> None:
        default = set(locales.ui(DEFAULT))
        for code in locales.others(DEFAULT):
            with self.subTest(code=code):
                self.assertEqual(sorted(set(locales.ui(code)) - default), [], f"config/ui/{code}.json has keys en.json lacks")

    def test_a_translation_keeps_the_placeholders_of_the_default(self) -> None:
        default = locales.ui(DEFAULT)
        for code in locales.others(DEFAULT):
            for key, text in locales.ui(code).items():
                with self.subTest(code=code, key=key):
                    self.assertEqual(set(PLACEHOLDER.findall(text)), set(PLACEHOLDER.findall(default[key])))

    def test_values_are_plain_text(self) -> None:
        for code in locales.LOCALES:
            for key, text in locales.ui(code).items():
                with self.subTest(code=code, key=key):
                    self.assertIsInstance(text, str)
                    self.assertTrue(text.strip(), "empty text")
                    self.assertNotIn('"', text, "use curly quotes; the dictionary is embedded as JSON and HTML")
                    self.assertNotRegex(text, r"</?[a-z]", "markup belongs in the template, not the dictionary")


class KeyUsageTest(unittest.TestCase):
    def test_every_key_a_call_names_exists_in_every_language(self) -> None:
        for code in locales.LOCALES:
            strings = locales.ui(code)
            for source, text in script_sources().items():
                named = tokens(text)
                for _, argument in first_arguments(text):
                    named |= set(re.findall(r"""['"]([\w.]+)['"]""", argument))
                with self.subTest(code=code, source=source):
                    self.assertEqual(sorted(named - set(strings)), [], f"{source} names keys config/ui/{code}.json lacks")

    def test_a_key_written_out_beside_its_use_exists(self) -> None:
        """A key chosen by a variable is spelled out where it is picked; a typo there would show as the key."""
        strings = set(locales.ui(DEFAULT))
        namespaces = {key.split(".", 1)[0] for key in strings}
        for source, text in script_sources().items():
            unknown = sorted(k for k in literal_keys(text) if k.split(".", 1)[0] in namespaces and k not in strings)
            with self.subTest(source=source):
                self.assertEqual(unknown, [], f"{source} has key-shaped text that is not in config/ui/en.json")

    def test_scripts_do_not_build_keys_from_pieces(self) -> None:
        """The build embeds only keys a script spells out, so a built key would read as itself."""
        for source, text in script_sources().items():
            for line, argument in first_arguments(text):
                with self.subTest(source=source, line=line):
                    self.assertFalse(builds_a_key(argument), f"{source}:{line} builds a key: {argument!r}")

    def test_the_scanner_tells_a_literal_key_from_a_built_one(self) -> None:
        self.assertFalse(builds_a_key("'feed.empty'"))
        self.assertFalse(builds_a_key("n === 1 ? 'a.one' : 'a.many'"))
        self.assertFalse(builds_a_key("key"))
        self.assertFalse(builds_a_key("keys[state]"))
        self.assertTrue(builds_a_key("'slot.' + slug"))
        self.assertTrue(builds_a_key("`slot.${slug}`"))
        calls = first_arguments("x = t('a.b', { n: f(1, 2) }) + tr(cond ? 'c.d' : 'e.f', 'x');\n// a t() call\nfunction t(key) {}")
        self.assertEqual([arg for _, arg in calls], ["'a.b'", "cond ? 'c.d' : 'e.f'"])

    def test_no_dictionary_key_is_dead(self) -> None:
        named: set[str] = set()
        for text in script_sources().values():
            named |= literal_keys(text) | tokens(text)
        python_side = (ROOT / "pipeline" / "render_static_pages.py").read_text(encoding="utf-8")
        named |= set(re.findall(r"""ui\[['"]([\w.]+)['"]\]""", python_side))
        dead = sorted(set(locales.ui(DEFAULT)) - named)
        self.assertEqual(dead, [], "remove keys nothing uses from config/ui/*.json")

    def test_external_script_fallbacks_match_the_default_dictionary(self) -> None:
        """Pages without a dictionary read the English text written beside each tr() call."""
        default = locales.ui(DEFAULT)
        call = re.compile(r"""\btr\(\s*(['"])([\w.]+)\1\s*,\s*((['"])(?:\\.|(?!\4).)*\4)""")
        checked = 0
        for name in EXTERNAL_SCRIPTS:
            text = (ROOT / "web" / f"{name}.js").read_text(encoding="utf-8")
            for match in call.finditer(text):
                key, literal = match.group(2), match.group(3)
                with self.subTest(script=name, key=key):
                    self.assertEqual(ast.literal_eval(literal), default[key])
                checked += 1
        self.assertGreater(checked, 50, "found too few tr() calls; the pattern drifted")


class TemplateTextTest(unittest.TestCase):
    """Text a reader sees must come from the dictionary, never from the template."""

    def test_template_text_outside_scripts_comes_from_the_dictionary(self) -> None:
        collector = _TextCollector()
        collector.feed(TEMPLATE)
        stray = sorted({text for text in collector.text if text not in STATIC_TEXT_ALLOWLIST})
        self.assertEqual(stray, [], "move this text to config/ui/*.json and use {{t:key}} in the template")

    def test_the_collector_sees_what_it_should(self) -> None:
        collector = _TextCollector()
        collector.feed(
            '<p title="Hello" class="x">Plain <b>bold</b> {{t:a}}</p><script>var s = "hidden";</script>'
            '<style>.a{}</style><!-- note --><a aria-label="{{t:b}}">12 🔍</a><kbd>Esc</kbd>'
            '<meta name="description" content="Words" />'
        )
        self.assertEqual(sorted(collector.text), ["Hello", "Plain", "Words", "bold"])


class _TextCollector(HTMLParser):
    """Collects reader-visible static text that is not a dictionary token or a bare number."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text: list[str] = []
        self._skip = 0

    def _add(self, raw: str) -> None:
        text = re.sub(r"\{\{[^{}]+\}\}", "", raw).strip()
        if re.search(r"[^\W\d_]", text):  # no letters means a number, symbol, or icon
            self.text.append(re.sub(r"\s+", " ", text))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style", "kbd"):
            self._skip += 1
            return
        values = dict(attrs)
        for name in TEXT_ATTRIBUTES:
            if values.get(name):
                self._add(values[name])
        if tag == "meta" and any((key, values.get(key)) in META_TEXT for key in ("name", "property")):
            self._add(values.get("content") or "")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "kbd"):
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._add(data)


if __name__ == "__main__":
    unittest.main()
