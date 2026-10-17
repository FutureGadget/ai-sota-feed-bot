#!/usr/bin/env python3
"""Pick the recap that needs an explainer video.

Usage: video_target.py [--kind daily|weekly]   (default: daily)

Prints JSON: {"due": bool, "id": str, "date": str, "reason": str}. `id` is the
recap key (`YYYY-MM-DD` for daily, `YYYY-Www` for weekly); `date` repeats it
for daily so older callers keep working.
Target = newest published recap in data/<kind>/index.json that has no `video`
field. Only the two newest recaps are considered, so a long-missed recap is
never back-filled.
"""
import argparse, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
KEY = {"daily": "date", "weekly": "week"}

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=sorted(KEY), default="daily")
    a = ap.parse_args()
    folder = ROOT / "data" / a.kind
    key = KEY[a.kind]
    index = json.loads((folder / "index.json").read_text(encoding="utf-8"))
    for row in index[:2]:
        recap = json.loads((folder / row["path"]).read_text(encoding="utf-8"))
        if not recap.get("video"):
            print(json.dumps({"due": True, "id": row[key], "date": row[key], "kind": a.kind,
                              "reason": "newest recap without video"}))
            return
    newest = index[0][key] if index else ""
    print(json.dumps({"due": False, "id": newest, "date": newest, "kind": a.kind,
                      "reason": "newest recaps already have video"}))

if __name__ == "__main__":
    main()
