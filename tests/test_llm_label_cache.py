"""Regression tests for the llm_label cache keying.

These guard the "outdated results" bug: the label cache used to be keyed only on
item id + config, so (a) flipping the LLM on served stale pre-LLM (heuristic)
labels, and (b) an item whose content changed kept its old label forever.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))

import llm_label  # noqa: E402


def _fresh_cache(tmp_path):
    cache = tmp_path / "labels.json"
    llm_label.CACHE_FILE_V2 = cache
    llm_label.CACHE_FILE = cache
    return cache


def _item(**over):
    base = {
        "id": "demo-id-1",
        "source": "anthropic_blog",
        "url": "https://example.com/post",
        "title": "New agentic feature",
        "summary": "Original summary text",
        "content_excerpt": "Original content excerpt",
    }
    base.update(over)
    return base


def test_same_item_same_mode_is_cached(tmp_path, monkeypatch):
    _fresh_cache(tmp_path)
    monkeypatch.setattr(llm_label, "load_cfg", lambda: {"enabled": False, "cache_version": 1})
    it = _item()

    _, meta1 = llm_label.label_items([it], budget=40, rubric_version="v2.1")
    _, meta2 = llm_label.label_items([it], budget=40, rubric_version="v2.1")

    assert meta1["cache_hits"] == 0
    assert meta2["cache_hits"] == 1  # unchanged item re-served from cache


def test_content_change_busts_cache(tmp_path, monkeypatch):
    _fresh_cache(tmp_path)
    monkeypatch.setattr(llm_label, "load_cfg", lambda: {"enabled": False, "cache_version": 1})

    out1, _ = llm_label.label_items([_item()], budget=40, rubric_version="v2.1")
    # Same id+url+title, but the article body / summary was updated.
    out2, meta2 = llm_label.label_items(
        [_item(summary="Completely rewritten summary", content_excerpt="updated body")],
        budget=40,
        rubric_version="v2.1",
    )

    assert meta2["cache_hits"] == 0  # updated content forces a re-label
    assert out2["demo-id-1"]["summary_1line"] != out1["demo-id-1"]["summary_1line"]


def test_enabling_llm_does_not_serve_heuristic_cache(tmp_path, monkeypatch):
    """The core 'outdated results' reproduction: a label cached while the LLM was
    off must NOT be served once the LLM is turned on."""
    _fresh_cache(tmp_path)
    it = _item()

    monkeypatch.setattr(llm_label, "load_cfg", lambda: {"enabled": False, "cache_version": 1})
    _, meta_off = llm_label.label_items([it], budget=40, rubric_version="v2.1")
    assert meta_off["cache_hits"] == 0

    # Operator turns the LLM on.
    monkeypatch.setattr(llm_label, "load_cfg", lambda: {"enabled": True, "cache_version": 1})
    _, meta_on = llm_label.label_items([it], budget=40, rubric_version="v2.1")

    # The pre-LLM (heuristic) cache entry from the off run must be ignored.
    assert meta_on["cache_hits"] == 0


if __name__ == "__main__":
    import tempfile

    class _MP:
        def setattr(self, obj, name, val):
            setattr(obj, name, val)

    for fn in (
        test_same_item_same_mode_is_cached,
        test_content_change_busts_cache,
        test_enabling_llm_does_not_serve_heuristic_cache,
    ):
        fn(Path(tempfile.mkdtemp()), _MP())
        print(f"ok: {fn.__name__}")
