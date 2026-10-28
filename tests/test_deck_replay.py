"""Labeling packets never overwrite owner grades; labeled metrics."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "pipeline"))

import deck_replay as dr  # noqa: E402


def result(published, selected, budget=2):
    stories = {sid: {"story_id": sid, "title": sid.upper(), "url": f"https://x/{sid}", "source": "s"} for sid in set(published) | set(selected)}
    return {"label": "2026-10-27", "published_ids": published, "selected_ids": selected, "budget": budget, "_stories": stories}


class PacketTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        patcher = patch.object(dr, "LABELS_DIR", Path(self._tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)

    def test_packet_prefills_agreements_and_keeps_owner_grades(self):
        path, added, pending = dr.write_packet("daily", result(["a", "b"], ["a", "c"]), set())
        data = json.loads(path.read_text())
        self.assertEqual((added, pending), (3, 2))
        self.assertEqual(data["stories"]["a"]["picked_by"], "both")
        self.assertEqual(data["stories"]["a"]["grade"], 1)
        self.assertIsNone(data["stories"]["b"]["grade"])

        data["stories"]["b"]["grade"] = 2
        data["stories"]["a"]["grade"] = 0
        path.write_text(json.dumps(data))
        _, added, pending = dr.write_packet("daily", result(["a", "b"], ["a", "d"]), set())
        data = json.loads(path.read_text())
        self.assertEqual(added, 1)  # only d is new
        self.assertEqual(data["stories"]["b"]["grade"], 2)
        self.assertEqual(data["stories"]["a"]["grade"], 0)
        self.assertEqual(pending, 2)  # c and d

    def test_labeled_metrics_compare_both_lists(self):
        path, _, _ = dr.write_packet("daily", result(["a", "b"], ["a", "c"]), set())
        data = json.loads(path.read_text())
        data["stories"]["b"]["grade"] = 0
        data["stories"]["c"]["grade"] = 2
        path.write_text(json.dumps(data))
        metrics = dr.labeled_metrics("daily", result(["a", "b"], ["a", "c"]))
        self.assertEqual(metrics["must"], 1)
        self.assertEqual(metrics["published"]["must_cover_recall"], 0.0)
        self.assertEqual(metrics["selector"]["must_cover_recall"], 1.0)
        self.assertEqual(metrics["published"]["drops"], 1)
        self.assertGreater(metrics["selector"]["alpha_ndcg"], metrics["published"]["alpha_ndcg"])
        self.assertEqual(metrics["selector"]["unlabeled"], 0)
        swapped = dr.labeled_metrics("daily", result(["a", "b"], ["a", "z"]))
        self.assertEqual(swapped["selector"]["unlabeled"], 1)


if __name__ == "__main__":
    unittest.main()
