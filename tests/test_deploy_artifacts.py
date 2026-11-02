"""Deployment artifact checks for the Cloudflare Worker deployment.

The Vercel function-bundle model is retired, so the guards are requirements
hygiene (the deploy build installs them), the Worker bundle size, and the
Workers Assets file-count ceiling that pre-rendered pages can creep toward.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_deploy_artifacts as cda  # noqa: E402


def test_current_repo_passes():
    assert cda.check_requirements(cda.REQUIREMENTS) == []
    assert cda.check_worker_bundle(cda.WORKER_DIR)[0] == []
    assert cda.check_handler_layout(cda.API_DIR) == []
    assert cda.check_static_assets(cda.WEB_DIR)[0] == []


def test_requirements_hygiene_flags_heavy_packages(tmp_path):
    path = tmp_path / "requirements.txt"
    path.write_text("requests==2.32\npandas==2.2\n", encoding="utf-8")
    errors = cda.check_requirements(path)
    assert any("pandas" in error for error in errors)


def test_requirements_hygiene_flags_package_budget(tmp_path):
    path = tmp_path / "requirements.txt"
    path.write_text("\n".join(f"pkg{i}" for i in range(cda.MAX_ROOT_REQUIREMENTS_COUNT + 1)))
    assert any("budget" in error for error in cda.check_requirements(path))


def test_worker_bundle_budget(tmp_path):
    worker = tmp_path / "worker"
    (worker / "src").mkdir(parents=True)
    (worker / "src" / "index.js").write_text("x" * 2048)
    errors, size_mb = cda.check_worker_bundle(worker, max_mb=0.001)
    assert errors and size_mb > 0
    assert cda.check_worker_bundle(worker, max_mb=5.0)[0] == []


def test_worker_bundle_ignores_node_modules(tmp_path):
    worker = tmp_path / "worker"
    (worker / "node_modules" / "big").mkdir(parents=True)
    (worker / "node_modules" / "big" / "index.js").write_text("x" * 2048)
    (worker / "src").mkdir()
    (worker / "src" / "index.js").write_text("x")
    _errors, size_mb = cda.check_worker_bundle(worker, max_mb=5.0)
    assert size_mb < 0.01


def test_asset_file_count_ceiling(tmp_path):
    web = tmp_path / "web"
    web.mkdir()
    for index in range(3):
        (web / f"p{index}.html").write_text("x")
    assert cda.check_static_assets(web, max_files=3)[0] == []
    errors, stats = cda.check_static_assets(web, max_files=2)
    assert errors and stats["files"] == 3


def test_oversized_single_asset_is_flagged(tmp_path):
    web = tmp_path / "web"
    web.mkdir()
    (web / "big.png").write_bytes(b"x" * (2 * 1024 * 1024))
    errors, _ = cda.check_static_assets(web, max_files=100, max_file_mb=1)
    assert any("big.png" in error for error in errors)


def test_nested_api_directory_is_flagged(tmp_path):
    api = tmp_path / "api"
    (api / "lib").mkdir(parents=True)
    (api / "feed.js").write_text("export const GET = () => null;\n")
    errors = cda.check_handler_layout(api)
    assert errors and "api/lib" in errors[0]
