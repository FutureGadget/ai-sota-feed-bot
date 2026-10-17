#!/usr/bin/env python3
"""Synthesize one WAV per scene with Gemini TTS (free tier per model: 3 requests/minute, 10/day).

Usage: gemini_tts.py narration.json OUT_DIR [--voice Kore] [--model ID]
Models are tried in quality order (MODELS). When one returns a per-day 429
(quota spent) or is unavailable, the script moves to the next for the rest of
the run. --model pins a single model with no fallback.
narration.json: [{"id": "s1", "text": "..."}, ...]  (max --max-scenes, default 12)

Auth: requests carry no credentials; the cloud agent proxy adds the
x-goog-api-key header. Existing clips are skipped, so a rerun spends no extra requests.
Send only the narration text: any style prefix is spoken aloud.
"""
import argparse, base64, json, os, sys, time, urllib.error, urllib.request

MODELS = ["gemini-3.8-flash-tts", "gemini-3.1-flash-tts-preview",
          "gemini-3.8-flash-lite-tts", "gemini-2.5-flash-preview-tts"]

ap = argparse.ArgumentParser()
ap.add_argument("narration"); ap.add_argument("out_dir"); ap.add_argument("--voice", default="Kore")
ap.add_argument("--model")
ap.add_argument("--max-scenes", type=int, default=12)
a = ap.parse_args()
models = [a.model] if a.model else list(MODELS)
URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"
scenes = json.load(open(a.narration))
if len(scenes) > a.max_scenes:
    sys.exit(f"max {a.max_scenes} scenes (each model allows 10 requests/day; the fallback chain spreads them)")
os.makedirs(a.out_dir, exist_ok=True)
headers = {"Content-Type": "application/json"}

for s in scenes:
    path = os.path.join(a.out_dir, f"{s['id']}.wav")
    if os.path.exists(path):
        continue
    body = {"contents": [{"parts": [{"text": s["text"]}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": a.voice}}}}}
    r = None
    while r is None:
        if not models:
            sys.exit(f"{s['id']}: every TTS model is out of quota or unavailable")
        for attempt in range(6):
            req = urllib.request.Request(URL.format(models[0]), json.dumps(body).encode(), headers)
            try:
                r = json.load(urllib.request.urlopen(req, timeout=120)); break
            except urllib.error.HTTPError as e:
                msg = e.read().decode()
                if e.code == 429 and "PerDay" not in msg and attempt < 5:
                    print(f"{s['id']}: 429, waiting 60s", file=sys.stderr); time.sleep(60); continue
                if (e.code == 429 or e.code in (400, 404)) and len(models) > 1:
                    print(f"{s['id']}: {models[0]} HTTP {e.code}, falling back", file=sys.stderr)
                    models.pop(0); break
                sys.exit(f"{s['id']}: {models[0]} HTTP {e.code} {msg[:300]}")
        else:
            sys.exit(f"{s['id']}: {models[0]} still rate limited")
    # 3.x models return a complete WAV; 2.5 returns raw PCM (wrapped below).
    pcm = base64.b64decode(r["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
    if pcm[:4] != b"RIFF":  # 2.5 models return raw 24 kHz mono s16le PCM
        import wave
        with wave.open(path, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
    else:
        open(path, "wb").write(pcm)
    print(f"{s['id']}: saved ({models[0]})", flush=True)
