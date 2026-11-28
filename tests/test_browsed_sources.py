"""Browsed sources: the registry contract and the x_watch collector type."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "collectors"))

import collect  # noqa: E402
from pipeline import editorial  # noqa: E402
from pipeline.sources_config import load_sources  # noqa: E402

NOW = datetime(2026, 11, 29, 6, 0, 0, tzinfo=timezone.utc)


def _slot_sources(path: Path, slot: str) -> set[str]:
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    return set(cfg["slots"][slot]["sources"])


def test_every_browsed_source_is_an_x_watch_entry_named_after_its_handle():
    browsed = load_sources("browsed")
    assert browsed
    for src in browsed:
        assert src["type"] == "x_watch"
        assert src["name"] == f"x_{src['handle'].lower()}"


def test_every_x_watch_source_is_mapped_to_the_posts_lane_in_both_configs():
    names = {s["name"] for s in load_sources() if s.get("type") == "x_watch"}
    assert names <= _slot_sources(ROOT / "config" / "ranking.yaml", "practitioner_posts")
    assert names <= _slot_sources(ROOT / "config" / "presets" / "balanced.yaml", "practitioner_posts")


def test_fetched_and_browsed_registries_do_not_share_names():
    fetched = {s["name"] for s in load_sources("fetched")}
    browsed = {s["name"] for s in load_sources("browsed")}
    assert fetched and browsed and not fetched & browsed


def test_duplicate_names_across_registries_are_rejected(tmp_path):
    sources = tmp_path / "config" / "sources"
    sources.mkdir(parents=True)
    (sources / "fetched.yaml").write_text("sources:\n  - name: a\n    type: rss\n")
    (sources / "browsed.yaml").write_text("sources:\n  - name: a\n    type: x_watch\n")
    with pytest.raises(ValueError, match="duplicate_source_name:a"):
        load_sources(root=tmp_path)


def test_x_sources_get_the_practitioner_role():
    assert editorial.source_role("x_karpathy") == "practitioner"


def _write_day(base: Path, day: str, posts: list[dict]) -> None:
    (base / "x").mkdir(parents=True, exist_ok=True)
    (base / "x" / f"{day}.json").write_text(json.dumps({"posts": posts}))


def test_x_watch_reads_the_handles_posts_from_recent_day_files(tmp_path, monkeypatch):
    monkeypatch.setattr(collect.sources_config, "BROWSED_DATA_DIR", tmp_path)
    long_line = "Agents " + "word " * 40
    _write_day(tmp_path, "2026-11-29", [
        {"handle": "karpathy", "author": "Andrej Karpathy", "url": "https://x.com/karpathy/status/2",
         "text": f"{long_line}\nsecond line", "published": "2026-11-29T01:00:00Z",
         "quoted": {"handle": "@simonw", "text": "quoted text", "url": "https://x.com/simonw/status/9"}},
        {"handle": "bcherny", "url": "https://x.com/bcherny/status/3", "text": "not mine"},
    ])
    _write_day(tmp_path, "2026-11-28", [
        {"handle": "Karpathy", "url": "https://x.com/karpathy/status/1", "text": "older post"},
        {"handle": "karpathy", "url": "https://x.com/karpathy/status/2", "text": "duplicate"},
    ])
    _write_day(tmp_path, "2026-11-25", [
        {"handle": "karpathy", "url": "https://x.com/karpathy/status/0", "text": "outside lookback"},
    ])

    items = collect.collect_from_x_watch({"name": "x_karpathy", "type": "x_watch", "handle": "karpathy"}, NOW)

    assert [i["url"] for i in items] == ["https://x.com/karpathy/status/2", "https://x.com/karpathy/status/1"]
    first = items[0]
    assert first["title"].endswith("…") and len(first["title"]) <= collect.X_TITLE_CHARS + 1
    assert "second line" in first["summary"]
    assert "Quoting @simonw: quoted text (https://x.com/simonw/status/9)" in first["summary"]
    assert first["publisher_name"] == "Andrej Karpathy (@karpathy)"
    assert first["publisher_domain"] == "x.com"
    assert items[1]["published"] == NOW.isoformat()


def test_x_watch_returns_nothing_when_no_day_file_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(collect.sources_config, "BROWSED_DATA_DIR", tmp_path)
    assert collect.collect_from_x_watch({"handle": "karpathy"}, NOW) == []


def _x_watch_script(tmp_path, monkeypatch):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "x_watch_script", ROOT / ".agents" / "skills" / "x-watch" / "scripts" / "x_watch.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "X_DIR", tmp_path / "x")
    return mod


def test_merge_validates_then_merges_idempotently(tmp_path, monkeypatch, capsys):
    mod = _x_watch_script(tmp_path, monkeypatch)
    good = {"handle": "KARPATHY", "url": "https://x.com/karpathy/status/12", "text": "hi",
            "published": "2026-11-29T01:00:00+00:00"}
    posts = tmp_path / "posts.json"
    posts.write_text(json.dumps([good]))

    assert mod.main(["merge", "--in", str(posts)], now=NOW) == 0
    assert mod.main(["merge", "--in", str(posts)], now=NOW) == 0
    saved = json.loads((tmp_path / "x" / "2026-11-29.json").read_text())["posts"]
    assert [p["handle"] for p in saved] == ["karpathy"]
    assert "added=0 total=1" in capsys.readouterr().out
    assert mod.main(["check"], now=NOW) == 0


def test_merge_rejects_unknown_accounts_and_mismatched_urls(tmp_path, monkeypatch, capsys):
    mod = _x_watch_script(tmp_path, monkeypatch)
    posts = tmp_path / "posts.json"
    posts.write_text(json.dumps([
        {"handle": "nobody", "url": "https://x.com/nobody/status/1", "text": "x", "published": "2026-11-29T01:00:00Z"},
        {"handle": "karpathy", "url": "https://x.com/bcherny/status/1", "text": "x", "published": "2026-11-29"},
    ]))
    assert mod.main(["merge", "--in", str(posts)], now=NOW) == 1
    out = capsys.readouterr().out
    assert "unknown_handle:nobody" in out and "bad_url:https://x.com/bcherny/status/1" in out
    assert "bad_published" in out
    assert not (tmp_path / "x").exists()


def test_plan_starts_each_account_after_its_newest_saved_post(tmp_path, monkeypatch, capsys):
    mod = _x_watch_script(tmp_path, monkeypatch)
    _write_day(tmp_path, "2026-11-28", [
        {"handle": "karpathy", "url": "https://x.com/karpathy/status/1", "text": "a",
         "published": "2026-11-28T20:00:00+00:00"},
    ])
    assert mod.main(["plan"], now=NOW) == 0
    plan = json.loads(capsys.readouterr().out)
    by_handle = {a["handle"]: a for a in plan["accounts"]}
    assert by_handle["karpathy"]["since"] == "2026-11-28T20:00:00+00:00"
    assert by_handle["bcherny"]["since"] == "2026-11-27T06:00:00+00:00"
    assert by_handle["HamelHusain"]["url"] == "https://x.com/HamelHusain"
