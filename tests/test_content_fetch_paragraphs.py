import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.content_fetch import extract_paragraphs, looks_like_code, strip_leading_code  # noqa: E402

PROSE = (
    "AI teams already train, fine-tune and serve their models on Verda, from dedicated GPU "
    "clusters to serverless containers that scale with demand. Today, we are adding the layer above."
)
SECOND = (
    "Verda Inference is our model-as-a-service offering, with OpenAI-compatible endpoints and "
    "per-token pricing for open-weight models served on the same GPU fleet our customers use."
)
# Minified scroll-spy script whose `o<p` comparison reads as an opening <p tag.
SCRIPT = (
    "<script>(()=>{const c=document.querySelectorAll('h2'),f=new Map,p=64;"
    "function b(){for(let o=0;o<p;o++){}}const t=new IntersectionObserver(e=>"
    "{for(const o of e)f.set(o.target.id,o.isIntersecting);b()},{rootMargin:`-${p}px 0px -60% 0px`,"
    "threshold:0});c.forEach(e=>t.observe(e))})();</script>"
)


class ExtractParagraphsTest(unittest.TestCase):
    def test_inline_script_never_leaks_into_paragraphs(self) -> None:
        raw = f"<html><body>{SCRIPT}<article><p>{PROSE}</p><p>{SECOND}</p></article></body></html>"
        text = extract_paragraphs(raw)
        self.assertTrue(text.startswith("AI teams already train"), text[:120])
        self.assertNotIn("isIntersecting", text)
        self.assertNotIn("rootMargin", text)

    def test_fallback_path_also_drops_scripts(self) -> None:
        raw = f"<html><body>{SCRIPT}<div>{PROSE}</div></body></html>"
        text = extract_paragraphs(raw)
        self.assertNotIn("isIntersecting", text)
        self.assertIn("AI teams already train", text)

    def test_code_paragraph_is_skipped(self) -> None:
        code = "for(const o of e)f.set(o.target.id,o.isIntersecting);b()},{rootMargin:`-${p}px`,threshold:0});"
        raw = f"<p>{code}</p><p>{PROSE}</p><p>{SECOND}</p>"
        self.assertNotIn("isIntersecting", extract_paragraphs(raw))

    def test_prose_with_one_inline_snippet_is_kept(self) -> None:
        prose = (
            "The fix was small: we replaced the retry loop with `const backoff = 2 ** attempt` and "
            "capped it at thirty seconds, which removed the thundering herd we saw after deploys."
        )
        self.assertFalse(looks_like_code(prose))


class StripLeadingCodeTest(unittest.TestCase):
    def test_removes_glued_script_prefix(self) -> None:
        bad = (
            "{for(const o of e)f.set(o.target.id,o.isIntersecting);b()},{rootMargin:`-${p}px 0px -60% 0px`,"
            "threshold:0});c.forEach(e=>t.observe(e)),s.push(()=>t.disconnect())}b()})}); "
            + PROSE + " " + SECOND
        )
        self.assertTrue(strip_leading_code(bad).startswith("AI teams already train"))

    def test_leaves_prose_alone(self) -> None:
        self.assertEqual(strip_leading_code(PROSE), PROSE)


if __name__ == "__main__":
    unittest.main()
