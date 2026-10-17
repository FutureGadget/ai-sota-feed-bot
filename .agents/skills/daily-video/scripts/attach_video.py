#!/usr/bin/env python3
"""Record an uploaded video on a recap and rebuild the daily pages.

Usage: attach_video.py --date YYYY-MM-DD --youtube-id ID --title T --duration-s N

Sets `video` on data/daily/<date>.json, validates, then runs
build_daily_index.py (index + latest + static page re-render). Only the id and
metadata are stored: the video file is never committed.
"""
import argparse, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DAILY_SCRIPTS = HERE.parents[1] / "daily-summary" / "scripts"
sys.path.insert(0, str(DAILY_SCRIPTS))
from daily_common import validate_recap  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--date", required=True); ap.add_argument("--youtube-id", required=True)
ap.add_argument("--title", required=True); ap.add_argument("--duration-s", type=float, required=True)
a = ap.parse_args()

path = HERE.parents[3] / "data" / "daily" / f"{a.date}.json"
recap = json.loads(path.read_text(encoding="utf-8"))
recap["video"] = {"youtube_id": a.youtube_id, "title": a.title, "duration_s": round(a.duration_s, 1)}
errors = validate_recap(recap)
if errors:
    sys.exit("invalid recap: " + "; ".join(errors))
path.write_text(json.dumps(recap, ensure_ascii=False, indent=2), encoding="utf-8")
subprocess.run([sys.executable, str(DAILY_SCRIPTS / "build_daily_index.py")], check=True)
print(f"video attached to {a.date}")
