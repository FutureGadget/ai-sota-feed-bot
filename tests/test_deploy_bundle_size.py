"""Tests for deployment bundle size, requirements budget, and .vercelignore integrity.

Prevents regressions that cause Vercel serverless function deployments to fail with
"A Serverless Function has exceeded the unzipped maximum size of 250 MB".
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import sys
sys.path.insert(0, str(ROOT / "scripts"))
import check_bundle_size as cbs


class DeployBundleSizeTest(unittest.TestCase):
    def test_repo_passes_all_checks(self):
        """The repository as committed must pass all bundle size and hygiene checks."""
        self.assertTrue(
            cbs.run_checks(root=ROOT, max_mb=150.0, verbose=False),
            "Deployment bundle size check failed on current repository tree!",
        )

    def test_requirements_hygiene_current(self):
        """Current root requirements.txt must contain no prohibited heavy packages."""
        errors = cbs.check_requirements(ROOT / "requirements.txt")
        self.assertEqual(errors, [])

    def test_requirements_hygiene_flags_prohibited_packages(self):
        """Adding heavy batch/offline dependencies to requirements.txt must be rejected."""
        prohibited_samples = [
            "pyarrow==18.1.0",
            "pandas>=2.0.0",
            "torch==2.1.0",
            "scipy",
            "numpy==1.26.0",
            "transformers",
        ]
        for sample in prohibited_samples:
            with self.subTest(pkg=sample):
                with tempfile.NamedTemporaryFile("w+", suffix=".txt") as tmp:
                    tmp.write(f"requests==2.32.3\n{sample}\n")
                    tmp.flush()
                    errors = cbs.check_requirements(Path(tmp.name))
                    self.assertTrue(
                        any("Prohibited heavy package" in e for e in errors),
                        f"Expected error for prohibited package '{sample}', got: {errors}",
                    )

    def test_requirements_hygiene_flags_budget_overflow(self):
        """Exceeding package count budget in root requirements.txt must be rejected."""
        with tempfile.NamedTemporaryFile("w+", suffix=".txt") as tmp:
            lines = [f"pkg{i}==1.0.0" for i in range(cbs.MAX_ROOT_REQUIREMENTS_COUNT + 5)]
            tmp.write("\n".join(lines))
            tmp.flush()
            errors = cbs.check_requirements(Path(tmp.name))
            self.assertTrue(
                any("max budget" in e for e in errors),
                f"Expected budget overflow error, got: {errors}",
            )

    def test_vercelignore_completeness_current(self):
        """Current .vercelignore must contain all required heavy directory entries."""
        errors = cbs.check_vercelignore(ROOT / ".vercelignore")
        self.assertEqual(errors, [])

    def test_vercelignore_completeness_catches_missing_entry(self):
        """Omitting a required heavy directory from .vercelignore must be caught."""
        with tempfile.NamedTemporaryFile("w+", suffix=".vercelignore") as tmp:
            tmp.write("data/raw\n.venv\n")
            tmp.flush()
            errors = cbs.check_vercelignore(Path(tmp.name))
            self.assertTrue(len(errors) > 0)
            self.assertTrue(any("data/tier1/runs" in e for e in errors))

    def test_function_bundle_sizes_under_budget(self):
        """Every function in vercel.json must remain well under the 150 MB safety budget."""
        errors, sizes = cbs.check_function_bundles(
            ROOT, ROOT / "vercel.json", max_mb=150.0, verbose=False
        )
        self.assertEqual(errors, [])
        for fn_name, size_mb in sizes.items():
            self.assertLess(
                size_mb,
                150.0,
                f"Function {fn_name} size ({size_mb:.2f} MB) exceeded 150 MB budget",
            )

    def test_function_bundle_exceeding_budget_reports_breakdown(self):
        """A function exceeding the configured budget must report an actionable error."""
        # Use an intentionally tiny budget of 1 MB to trigger the error on feed.js
        errors, sizes = cbs.check_function_bundles(
            ROOT, ROOT / "vercel.json", max_mb=1.0, verbose=False
        )
        self.assertTrue(len(errors) > 0)
        self.assertTrue(any("api/feed.js" in e and "exceeds maximum allowed" in e for e in errors))

    def test_expand_braces(self):
        """Brace expansion must correctly expand single and multi-option patterns."""
        self.assertEqual(cbs.expand_braces("data/plain.json"), ["data/plain.json"])
        self.assertEqual(
            cbs.expand_braces("data/{a,b}.json"),
            ["data/a.json", "data/b.json"],
        )
        self.assertEqual(
            cbs.expand_braces("data/{a,b}/{x,y}.json"),
            ["data/a/x.json", "data/a/y.json", "data/b/x.json", "data/b/y.json"],
        )


if __name__ == "__main__":
    unittest.main()
