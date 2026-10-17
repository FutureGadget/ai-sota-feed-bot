#!/usr/bin/env python3
"""Synthesize one WAV per scene with Gemini TTS (free tier: 10 requests/day).

Usage: gemini_tts.py narration.json OUT_DIR [--voice Kore]
narration.json: [{"id": "s1", "text": "..."}, ...]  (max 8 scenes)

Auth: requests carry no credentials; the cloud agent proxy adds the
x-goog-api-key header. For local testing only, ~/.gemini-api-key is sent when
it exists. Existing clips are skipped, so a rerun spends no extra requests.
Send only the narration text: any style prefix is spoken aloud.
"""
import argparse, base64, json, os, sys, time, urllib.error, urllib.request

MODEL = "gemini-3.8-flash-tts"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

ap = argparse.ArgumentParser()
ap.add_argument("narration"); ap.add_argument("out_dir"); ap.add_argument("--voice", default="Kore")
a = ap.parse_args()
scenes = json.load(open(a.narration))
if len(scenes) > 8:
    sys.exit("max 8 scenes (free tier is 10 requests/day)")
os.makedirs(a.out_dir, exist_ok=True)
headers = {"Content-Type": "application/json"}
_local_key = os.path.expanduser("~/.gemini-api-key")
if os.path.exists(_local_key):  # local testing only
    headers["x-goog-api-key"] = open(_local_key).read().strip()

for s in scenes:
    path = os.path.join(a.out_dir, f"{s['id']}.wav")
    if os.path.exists(path):
        continue
    body = {"contents": [{"parts": [{"text": s["text"]}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": a.voice}}}}}
    for attempt in range(6):
        req = urllib.request.Request(URL, json.dumps(body).encode(), headers)
        try:
            r = json.load(urllib.request.urlopen(req, timeout=120)); break
        except urllib.error.HTTPError as e:
            msg = e.read().decode()
            if e.code == 429 and "PerDay" not in msg and attempt < 5:
                print(f"{s['id']}: 429, waiting 60s", file=sys.stderr); time.sleep(60); continue
            sys.exit(f"{s['id']}: HTTP {e.code} {msg[:300]}")
    # inlineData is already a complete WAV: write the bytes as-is.
    open(path, "wb").write(base64.b64decode(r["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]))
    print(f"{s['id']}: saved", flush=True)
