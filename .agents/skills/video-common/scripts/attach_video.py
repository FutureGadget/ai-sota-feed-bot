#!/usr/bin/env python3
"""Record an uploaded video on a recap and rebuild its pages.

Usage: attach_video.py [--kind daily|weekly] --id KEY --youtube-id ID --title T --duration-s N
       (--date is accepted as an alias of --id for daily)

KEY is `YYYY-MM-DD` (daily) or `YYYY-Www` (weekly). Sets `video` on
data/<kind>/<KEY>.json, validates, then runs the kind's index builder (index +
latest + static page re-render). Only the id and metadata are stored: the video
file is never committed.
"""
import argparse, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parents[1]
KINDS = {
    "daily": (SKILLS / "daily-summary" / "scripts", "daily_common", "build_daily_index.py"),
    "weekly": (SKILLS / "weekly-summary" / "scripts", "weekly_common", "build_weekly_index.py"),
}

ap = argparse.ArgumentParser()
ap.add_argument("--kind", choices=sorted(KINDS), default="daily")
ap.add_argument("--id", "--date", dest="key", required=True)
ap.add_argument("--youtube-id", required=True)
ap.add_argument("--title", required=True); ap.add_argument("--duration-s", type=float, required=True)
a = ap.parse_args()

scripts, module, builder = KINDS[a.kind]
sys.path.insert(0, str(scripts))
validate_recap = __import__(module).validate_recap

path = HERE.parents[3] / "data" / a.kind / f"{a.key}.json"
recap = json.loads(path.read_text(encoding="utf-8"))
recap["video"] = {"youtube_id": a.youtube_id, "title": a.title, "duration_s": round(a.duration_s, 1)}
errors = validate_recap(recap)
if errors:
    sys.exit("invalid recap: " + "; ".join(errors))
path.write_text(json.dumps(recap, ensure_ascii=False, indent=2), encoding="utf-8")
subprocess.run([sys.executable, str(scripts / builder)], check=True)
print(f"video attached to {a.kind} {a.key}")
