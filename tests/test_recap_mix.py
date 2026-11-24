from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = {
    "daily": ROOT / ".agents" / "skills" / "daily-summary" / "scripts",
    "weekly": ROOT / ".agents" / "skills" / "weekly-summary" / "scripts",
}


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


daily_common = _load("daily_common", SCRIPTS["daily"] / "daily_common.py")
weekly_common = _load("weekly_common", SCRIPTS["weekly"] / "weekly_common.py")


def cards(hn: int, other: int = 4) -> list[dict]:
    rows = [{"title": f"hn {i}", "url": f"https://hn.example/{i}", "source": "hackernews_ai"} for i in range(hn)]
    rows += [{"title": f"blog {i}", "url": f"https://blog.example/{i}", "source": "openai_blog"} for i in range(other)]
    return rows


def daily(date: str, hn: int) -> dict:
    return {"date": date, "title": "t", "categories": [{"name": "c", "articles": cards(hn)}]}


def weekly(week: str, hn: int) -> dict:
    return {
        "week": week,
        "start": "2026-11-23",
        "end": "2026-11-29",
        "title": "t",
        "categories": [{"name": "c", "articles": cards(hn)}],
    }


def cap_errors(errors: list[str]) -> list[str]:
    return [e for e in errors if "community" in e]


class RecapCommunityCapTest(unittest.TestCase):
    def test_daily_recap_at_the_cap_is_valid(self) -> None:
        self.assertEqual(daily_common.validate_recap(daily("2026-11-25", 6)), [])

    def test_daily_recap_over_the_cap_is_rejected(self) -> None:
        errors = cap_errors(daily_common.validate_recap(daily("2026-11-25", 7)))
        self.assertEqual(len(errors), 1)
        self.assertIn("7 cards from community sources", errors[0])
        self.assertIn("at most 6", errors[0])

    def test_daily_archive_before_since_is_not_checked(self) -> None:
        self.assertEqual(daily_common.validate_recap(daily("2026-11-23", 25)), [])

    def test_weekly_cap_starts_at_its_own_week_id(self) -> None:
        self.assertEqual(weekly_common.validate_recap(weekly("2026-W47", 28)), [])
        self.assertEqual(weekly_common.validate_recap(weekly("2026-W48", 12)), [])
        self.assertEqual(len(cap_errors(weekly_common.validate_recap(weekly("2026-W48", 13)))), 1)

    def test_published_archives_still_validate(self) -> None:
        for kind in ("daily", "weekly"):
            script = SCRIPTS[kind] / f"build_{kind}_index.py"
            run = subprocess.run([sys.executable, str(script), "--check"], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, msg=f"{kind}: {run.stdout}\n{run.stderr}")


class PoolAdditionsMissingDependencyTest(unittest.TestCase):
    def test_missing_dependency_stops_the_bundle_and_names_it(self) -> None:
        # sys.modules[name] = None makes `import name` fail as if not installed.
        code = textwrap.dedent(
            f"""
            import sys
            sys.modules["dateutil"] = None
            sys.path.insert(0, {str(SCRIPTS["daily"])!r})
            from datetime import date
            import daily_common
            daily_common.add_pool_articles([], date(2026, 11, 23), date(2026, 11, 23), {{"news"}}, set())
            """
        )
        run = subprocess.run([sys.executable, "-c", code], cwd="/", capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("dateutil", run.stderr)
        self.assertNotIn("No module named 'pipeline'", run.stderr)

    def test_pool_additions_still_run_with_dependencies(self) -> None:
        code = textwrap.dedent(
            f"""
            import json, sys
            sys.path.insert(0, {str(SCRIPTS["daily"])!r})
            from datetime import date
            import daily_common
            _, diag = daily_common.add_pool_articles([], date(2026, 11, 23), date(2026, 11, 23), {{"news"}}, set())
            print(json.dumps(diag))
            """
        )
        run = subprocess.run([sys.executable, "-c", code], cwd="/", capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, msg=run.stderr)
        diag = json.loads(run.stdout.strip().splitlines()[-1])
        self.assertNotIn("error", diag)


if __name__ == "__main__":
    unittest.main()
