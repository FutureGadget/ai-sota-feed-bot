#!/usr/bin/env python3
"""Scene timing from audio clips, then final MP4 encode.

  assemble.py timing narration.json CLIPS_DIR   -> timing.json
  assemble.py encode FRAMES_DIR OUT.mp4         -> mixes clips + frames (needs timing.json)

Scene length = lead 0.9 s + clip + tail 2.7 s. Also warns when a clip is far
longer than the text predicts (about 2.5 words/second), which means something
besides the narration was spoken.
"""
import json, subprocess, sys

LEAD, TAIL = 0.9, 2.7

def dur(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]))

if sys.argv[1] == "timing":
    scenes = json.load(open(sys.argv[2])); clips = sys.argv[3]; t = 0; out = []
    for s in scenes:
        d = dur(f"{clips}/{s['id']}.wav")
        words = len(s["text"].split())
        if d > words / 2.5 * 1.8 + 1:
            print(f"WARNING {s['id']}: {d:.1f}s for {words} words, check the clip", file=sys.stderr)
        out.append(dict(id=s["id"], text=s["text"], start=round(t, 3), dur=round(LEAD + d + TAIL, 3), lead=LEAD, adur=round(d, 3)))
        t += LEAD + d + TAIL
    json.dump(dict(total=round(t, 3), scenes=out), open("timing.json", "w"), indent=1)
    print(f"total {t:.1f}s")
else:
    frames, out_mp4 = sys.argv[2], sys.argv[3]
    T = json.load(open("timing.json")); ins = []; fl = []
    for i, s in enumerate(T["scenes"]):
        ins += ["-i", f"clips/{s['id']}.wav"]; ms = int((s["start"] + s["lead"]) * 1000)
        fl.append(f"[{i}:a]adelay={ms}|{ms},apad[a{i}]")
    mix = "".join(f"[a{i}]" for i in range(len(fl)))
    fc = ";".join(fl) + f";{mix}amix=inputs={len(fl)}:normalize=0,atrim=0:{T['total']}[o]"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *ins, "-filter_complex", fc, "-map", "[o]", "narration.wav"], check=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", "30", "-i", f"{frames}/f%05d.jpg", "-i", "narration.wav",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                    "-shortest", "-movflags", "+faststart", out_mp4], check=True)
    print(json.dumps({"file": out_mp4, "duration_s": round(dur(out_mp4), 1)}))
