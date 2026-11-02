"""Deployment artifact checks for the Cloudflare Worker deployment.

The Vercel function-bundle model is retired, so the guards are requirements
hygiene (the deploy build installs them), the Worker bundle size, and the
Workers Assets file-count ceiling that pre-rendered pages can creep toward.

Run by `python -m unittest discover` in CI, so this file must not import pytest.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_deploy_artifacts as cda  # noqa: E402


class DeployArtifactsTest(unittest.TestCase):
    def test_current_repo_passes(self) -> None:
        self.assertEqual(cda.check_requirements(cda.REQUIREMENTS), [])
        self.assertEqual(cda.check_worker_bundle(cda.WORKER_DIR)[0], [])
        self.assertEqual(cda.check_handler_layout(cda.API_DIR), [])
        self.assertEqual(cda.check_static_assets(cda.WEB_DIR)[0], [])

    def test_requirements_hygiene_flags_heavy_packages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "requirements.txt"
            path.write_text("requests==2.32\npandas==2.2\n", encoding="utf-8")
            errors = cda.check_requirements(path)
        self.assertTrue(any("pandas" in error for error in errors))

    def test_requirements_hygiene_flags_package_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "requirements.txt"
            path.write_text(
                "\n".join(f"pkg{i}" for i in range(cda.MAX_ROOT_REQUIREMENTS_COUNT + 1)),
                encoding="utf-8",
            )
            errors = cda.check_requirements(path)
        self.assertTrue(any("budget" in error for error in errors))

    def test_worker_bundle_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            worker = Path(tmp) / "worker"
            (worker / "src").mkdir(parents=True)
            (worker / "src" / "index.js").write_text("x" * 2048)
            errors, size_mb = cda.check_worker_bundle(worker, max_mb=0.001)
            self.assertTrue(errors)
            self.assertGreater(size_mb, 0)
            self.assertEqual(cda.check_worker_bundle(worker, max_mb=5.0)[0], [])

    def test_worker_bundle_ignores_node_modules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            worker = Path(tmp) / "worker"
            (worker / "node_modules" / "big").mkdir(parents=True)
            (worker / "node_modules" / "big" / "index.js").write_text("x" * 2048)
            (worker / "src").mkdir()
            (worker / "src" / "index.js").write_text("x")
            _errors, size_mb = cda.check_worker_bundle(worker, max_mb=5.0)
        self.assertLess(size_mb, 0.01)

    def test_asset_file_count_ceiling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            web = Path(tmp) / "web"
            web.mkdir()
            for index in range(3):
                (web / f"p{index}.html").write_text("x")
            self.assertEqual(cda.check_static_assets(web, max_files=3)[0], [])
            errors, stats = cda.check_static_assets(web, max_files=2)
        self.assertTrue(errors)
        self.assertEqual(stats["files"], 3)

    def test_oversized_single_asset_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            web = Path(tmp) / "web"
            web.mkdir()
            (web / "big.png").write_bytes(b"x" * (2 * 1024 * 1024))
            errors, _ = cda.check_static_assets(web, max_files=100, max_file_mb=1)
        self.assertTrue(any("big.png" in error for error in errors))

    def test_nested_api_directory_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = Path(tmp) / "api"
            (api / "lib").mkdir(parents=True)
            (api / "feed.js").write_text("export const GET = () => null;\n")
            errors = cda.check_handler_layout(api)
        self.assertTrue(errors)
        self.assertIn("api/lib", errors[0])


if __name__ == "__main__":
    unittest.main()
