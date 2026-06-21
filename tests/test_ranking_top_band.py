from __future__ import annotations

import unittest

from pipeline.ranking import enforce_top_band_constraints


def _item(source: str, slot: str, global_score: float, **extra) -> dict:
    it = {
        "source": source,
        "slot": slot,
        "global_score": global_score,
        "url": f"https://example.com/{source}/{global_score}",
        "title": f"{source} {global_score}",
    }
    it.update(extra)
    return it


class LeadExcludesResearchTest(unittest.TestCase):
    """The lead (position 0) should not be a niche research paper when any
    non-research item exists in the band — but the rest of the band keeps its
    global_score order and the research-count cap still holds."""

    CFG = {
        "top_band_constraints": {
            "enabled": True,
            "top_n": 10,
            "min_frontier_official": 0,
            "min_anthropic_frontier": 0,
            "max_research_in_top_n": 3,
            "lead_excludes_research": True,
        }
    }

    def test_lifts_best_non_research_to_lead(self) -> None:
        items = [
            _item("arxiv_cs_ai", "research_watch", 3.15),
            _item("arxiv_cs_lg", "research_watch", 2.89),
            _item("simon_willison", "practitioner_analysis", 2.76),
            _item("openai_blog", "frontier_official", 2.71),
        ]
        out, diag = enforce_top_band_constraints(items, self.CFG)
        self.assertEqual(diag["lead_lifted"], 1)
        self.assertEqual(out[0]["source"], "simon_willison")  # best non-research
        # The displaced papers keep their relative order right behind the lead.
        self.assertEqual([x["source"] for x in out[1:4]], ["arxiv_cs_ai", "arxiv_cs_lg", "openai_blog"])

    def test_research_category_also_counts_as_research(self) -> None:
        items = [
            _item("anthropic_research", "research_watch", 3.0, llm_category="research"),
            _item("infoq_ai_ml", "practitioner_analysis", 2.5),
        ]
        out, diag = enforce_top_band_constraints(items, self.CFG)
        self.assertEqual(out[0]["source"], "infoq_ai_ml")
        self.assertEqual(diag["lead_lifted"], 1)

    def test_noop_when_band_is_all_research(self) -> None:
        items = [
            _item("arxiv_cs_ai", "research_watch", 3.15),
            _item("arxiv_cs_lg", "research_watch", 2.89),
        ]
        out, diag = enforce_top_band_constraints(items, self.CFG)
        self.assertEqual(diag["lead_lifted"], 0)
        self.assertEqual(out[0]["source"], "arxiv_cs_ai")  # unchanged

    def test_noop_when_lead_already_non_research(self) -> None:
        items = [
            _item("openai_blog", "frontier_official", 3.0),
            _item("arxiv_cs_ai", "research_watch", 2.9),
        ]
        out, diag = enforce_top_band_constraints(items, self.CFG)
        self.assertEqual(diag["lead_lifted"], 0)
        self.assertEqual(out[0]["source"], "openai_blog")

    def test_disabled_knob_leaves_research_lead(self) -> None:
        cfg = {"top_band_constraints": {**self.CFG["top_band_constraints"], "lead_excludes_research": False}}
        items = [
            _item("arxiv_cs_ai", "research_watch", 3.15),
            _item("simon_willison", "practitioner_analysis", 2.76),
        ]
        out, diag = enforce_top_band_constraints(items, cfg)
        self.assertEqual(diag["lead_lifted"], 0)
        self.assertEqual(out[0]["source"], "arxiv_cs_ai")


if __name__ == "__main__":
    unittest.main()
