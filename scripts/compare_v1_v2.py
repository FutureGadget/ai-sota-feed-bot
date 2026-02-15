from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: Path):
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def item_key(x: dict) -> str:
    return x.get("id") or x.get("url") or f"{x.get('source')}::{x.get('title')}"


def provider_of(src: str) -> str:
    s = (src or "").lower()
    if s.startswith("openai") or "codex" in s:
        return "openai"
    if s.startswith("anthropic") or "claude_code" in s:
        return "anthropic"
    return "other"


def main() -> None:
    v1 = load(ROOT / "data" / "processed" / "latest.json")
    v2 = load(ROOT / "data" / "processed" / "latest_v2.json")

    if not v1 or not v2:
        print("compare_v1_v2 skipped (missing latest.json or latest_v2.json)")
        return

    k1 = {item_key(x) for x in v1}
    k2 = {item_key(x) for x in v2}
    inter = k1 & k2
    union = k1 | k2
    jacc = (len(inter) / len(union)) if union else 0.0

    print(f"v1_items={len(v1)} v2_items={len(v2)} overlap={len(inter)} jaccard={jacc:.3f}")

    c1 = Counter(x.get("source", "unknown") for x in v1)
    c2 = Counter(x.get("source", "unknown") for x in v2)
    print("v1_top_sources", c1.most_common(8))
    print("v2_top_sources", c2.most_common(8))

    p1 = Counter(provider_of(x.get("source", "")) for x in v1)
    p2 = Counter(provider_of(x.get("source", "")) for x in v2)
    print("v1_provider", dict(p1))
    print("v2_provider", dict(p2))


if __name__ == "__main__":
    main()
