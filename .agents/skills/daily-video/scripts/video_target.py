#!/usr/bin/env python3
"""Pick the recap that needs an explainer video.

Prints JSON: {"due": bool, "date": "YYYY-MM-DD", "reason": str}.
Target = newest published recap in data/daily/index.json that has no `video`
field. Only the two newest recaps are considered, so a long-missed day is
never back-filled.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DAILY = ROOT / "data" / "daily"

def main() -> None:
    index = json.loads((DAILY / "index.json").read_text(encoding="utf-8"))
    for row in index[:2]:
        recap = json.loads((DAILY / row["path"]).read_text(encoding="utf-8"))
        if not recap.get("video"):
            print(json.dumps({"due": True, "date": row["date"], "reason": "newest recap without video"}))
            return
    print(json.dumps({"due": False, "date": index[0]["date"] if index else "", "reason": "newest recaps already have video"}))

if __name__ == "__main__":
    main()
