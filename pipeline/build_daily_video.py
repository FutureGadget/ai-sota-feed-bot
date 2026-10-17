"""Render the curated daily recap as a short narrated news video.

Input is ``data/daily/<date>.json`` (or ``latest.json``), the same curated
recap the ``/daily`` page and the email brief render. The script is
deterministic: an opening scene (title + intro), a headlines scene, one scene
per recap category, and a closing call to the full brief. Each scene becomes a
1920x1080 broadsheet-style slide (``pipeline/og_cards.py`` palette and fonts)
plus a narration line.

Narration uses the Gemini API TTS model (free tier) when ``GEMINI_API_KEY`` is
set. It is optional and non-fatal: without a key, or when a request fails or is
rate limited, the affected scenes are silent and timed from the word count, so
the video still builds. Output goes to ``build/daily-video/<date>/`` (not
committed): ``<date>.mp4``, ``<date>.vtt``, ``script.json`` and the slides.

    python3 pipeline/build_daily_video.py            # latest recap
    python3 pipeline/build_daily_video.py --date 2026-10-16 --no-tts
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import og_cards as og  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DAILY_DIR = ROOT / "data" / "daily"
OUT_ROOT = ROOT / "build" / "daily-video"

W, H = 1920, 1080
MARGIN = 120
SAMPLE_RATE = 24000
GAP_SECONDS = 0.5
WORDS_PER_SECOND = 2.6  # silent-scene pacing
MIN_SCENE_SECONDS = 4.0
MAX_CATEGORY_ARTICLES = 3
MAX_STATS = 4
SECONDS_PER_STORY = 2.2  # motion scenes need time for each card to animate in
VIDEO_DIR = ROOT / "video"
# A figure only counts as a callout with a unit or $ ("501B", "5-hour", "$2M",
# "40%"); bare numbers like "Beam-1.0" or "day-0" are version/label noise.
STAT_RE = re.compile(
    r"(?<![\w.])(\$)?(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)"
    r"(\s?(?:[BMKT]|%|x|GB|TB|ms)|-?\s?(?:hours?|minutes?|days?))?(?![\w])"
)

TTS_MODEL = os.environ.get("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
TTS_VOICE = os.environ.get("GEMINI_TTS_VOICE", "Kore")
TTS_STYLE = "calm, clear newsreader pace"
TTS_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"
TTS_TIMEOUT = 90
TTS_PACE_SECONDS = float(os.environ.get("GEMINI_TTS_PACE_SECONDS", "6"))


def load_recap(date: str | None) -> dict:
    path = DAILY_DIR / (f"{date}.json" if date else "latest.json")
    return json.loads(path.read_text(encoding="utf-8"))


def _clean(text: str) -> str:
    return " ".join(str(text or "").split())


def _spoken_date(date: str) -> str:
    import datetime as dt

    d = dt.date.fromisoformat(date)
    return f"{d.strftime('%A, %B')} {d.day}"


def extract_stat(text: str) -> dict | None:
    """First unit-bearing figure in ``text`` as a count-up callout, else None."""
    for m in STAT_RE.finditer(text):
        prefix, num, unit = m.group(1) or "", m.group(2), (m.group(3) or "")
        value = float(num.replace(",", ""))
        if not (prefix or unit.strip()) or value == 0 or (1900 <= value <= 2100 and not unit):
            continue
        suffix = unit.strip() if unit.strip() in ("B", "M", "K", "T", "%", "x", "GB", "TB", "ms") else ""
        unit_label = "" if suffix else re.sub(r"[-\s]+", " ", unit).strip()
        return {
            "value": value,
            "prefix": prefix,
            "suffix": suffix or (f" {unit_label}" if unit_label else ""),
            "decimals": len(num.split(".")[1]) if "." in num else 0,
        }
    return None


def _source_name(source: str) -> str:
    return re.sub(r"\s+", " ", str(source or "").replace("_", " ")).strip()


def build_scenes(recap: dict) -> list[dict]:
    """Deterministic scene list: {kind, kicker, heading, bullets, narration}."""
    date = recap["date"]
    scenes: list[dict] = []
    intro = [_clean(x) for x in recap.get("intro") or [] if _clean(x)]
    scenes.append(
        {
            "kind": "open",
            "kicker": "The finishable daily brief",
            "heading": _clean(recap.get("title") or f"What happened in AI — {date}"),
            "bullets": intro,
            "narration": " ".join([f"LLM Digest, {_spoken_date(date)}.", *intro]),
        }
    )
    highlights = [_clean(x) for x in recap.get("highlights") or [] if _clean(x)]
    if highlights:
        scenes.append(
            {
                "kind": "highlights",
                "kicker": "Top headlines",
                "heading": "Today at a glance",
                "bullets": highlights[:6],
                "narration": " ".join(["The headlines."] + highlights[:6]),
            }
        )
    stats = []
    for text in highlights:
        st = extract_stat(text)
        if st:
            stats.append({**st, "label": text})
    if stats:
        scenes.append(
            {
                "kind": "stats",
                "kicker": "By the numbers",
                "heading": "The figures behind the headlines",
                "stats": stats[:MAX_STATS],
                "bullets": [x["label"] for x in stats[:MAX_STATS]],
                "narration": "A few of the numbers behind those headlines.",
            }
        )
    for cat in recap.get("categories") or []:
        arts = [a for a in cat.get("articles") or [] if _clean(a.get("title"))]
        if not arts:
            continue
        titles = [_clean(a["title"]) for a in arts[:MAX_CATEGORY_ARTICLES]]
        more = len(arts) - len(titles)
        summary = _clean(cat.get("summary"))
        narration = " ".join([f"{_clean(cat.get('name'))}.", summary])
        scenes.append(
            {
                "kind": "category",
                "kicker": f"{len(arts)} {'story' if len(arts) == 1 else 'stories'}",
                "heading": _clean(cat.get("name")),
                "dek": summary,
                "total": len(arts),
                "stories": [
                    {
                        "title": _clean(a["title"]),
                        "summary": _clean(a.get("summary")),
                        "source": _source_name(a.get("source")),
                        **({"stat": st} if (st := extract_stat(_clean(a["title"]))) else {}),
                    }
                    for a in arts[:MAX_CATEGORY_ARTICLES]
                ],
                "bullets": titles + ([f"+{more} more in the full brief"] if more > 0 else []),
                "narration": narration,
            }
        )
    scenes.append(
        {
            "kind": "close",
            "kicker": "You're caught up",
            "heading": "Read the full brief",
            "bullets": ["llm-digest.com/daily"],
            "narration": "That's the brief. Full stories and sources are at llm-digest dot com slash daily.",
        }
    )
    return scenes


# ---------------------------------------------------------------- slides


def render_slide(scene: dict, index: int, total: int, date: str) -> "og.Image.Image":
    img = og.Image.new("RGB", (W, H), og.PAPER)
    d = og.ImageDraw.Draw(img)
    text_w = W - 2 * MARGIN

    d.text((MARGIN, 52), og.BRAND, font=og.serif("display", 56), fill=og.INK)
    date_font = og.serif("text", 34)
    d.text((W - MARGIN - d.textlength(date, font=date_font), 70), date, font=date_font, fill=og.MUTED)
    og.double_rule(d, 142, MARGIN, W - MARGIN)

    og.draw_label(d, (MARGIN, 190), scene["kicker"], 28, og.RED)

    heading = scene["heading"]
    size, max_lines = (84, 2) if scene["kind"] != "open" else (92, 3)
    font = og.serif("display", size, heading)
    lines = og.wrap(d, heading, font, text_w, max_lines)
    y = 240
    for line in lines:
        d.text((MARGIN, y), line, font=font, fill=og.INK)
        y += int(size * 1.12)
    y += 20

    dek = scene.get("dek")
    if dek:
        dek_font = og.serif("italic", 38, dek)
        for line in og.wrap(d, dek, dek_font, text_w, 3):
            d.text((MARGIN, y), line, font=dek_font, fill=og.MUTED)
            y += 52
        y += 16

    body_font = og.serif("text", 40, " ".join(scene["bullets"]))
    footer_y = H - 130
    for bullet in scene["bullets"]:
        if y > footer_y - 60:
            break
        lines = og.wrap(d, bullet, body_font, text_w - 48, 2)
        d.rectangle((MARGIN, y + 20, MARGIN + 12, y + 32), fill=og.RED)
        for line in lines:
            d.text((MARGIN + 48, y), line, font=body_font, fill=og.INK)
            y += 54
        y += 18

    d.line((MARGIN, footer_y, W - MARGIN, footer_y), fill=og.RULE, width=2)
    og.draw_label(d, (MARGIN, footer_y + 34), og.URL, 26, og.MUTED)
    og.draw_label(d, (W - MARGIN, footer_y + 34), f"{index} / {total}", 26, og.MUTED, align="right")
    return img


# ------------------------------------------------------------------ TTS


def _pcm_from_wav(data: bytes) -> bytes:
    with wave.open(io.BytesIO(data)) as w:
        if (w.getnchannels(), w.getsampwidth(), w.getframerate()) != (1, 2, SAMPLE_RATE):
            raise ValueError("unexpected wav format")
        return w.readframes(w.getnframes())


def synthesize(text: str, api_key: str) -> bytes:
    """Return 24 kHz mono 16-bit PCM for ``text`` (raises on any failure)."""
    body = {
        "model": TTS_MODEL,
        "input": [
            {
                "type": "user_input",
                "content": [
                    {
                        "type": "text",
                        "text": text,
                        "annotations": [{"type": "speech_metadata", "style": TTS_STYLE}],
                    }
                ],
            }
        ],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": TTS_VOICE}]},
    }
    resp = requests.post(
        TTS_ENDPOINT,
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json=body,
        timeout=TTS_TIMEOUT,
    )
    resp.raise_for_status()
    audio = [
        c
        for step in resp.json().get("steps", [])
        if step.get("type") == "model_output"
        for c in step.get("content", [])
        if c.get("type") == "audio"
    ]
    if not audio:
        raise ValueError("no audio in response")
    return _pcm_from_wav(base64.b64decode(audio[-1]["data"]))


def narrate(scenes: list[dict], api_key: str | None) -> None:
    """Fill ``scene['pcm']`` where TTS succeeds; stop calling after a hard failure."""
    ok = failed = 0
    stopped = not api_key
    for i, scene in enumerate(scenes):
        scene["pcm"] = b""
        if stopped:
            continue
        if i:
            time.sleep(TTS_PACE_SECONDS)
        try:
            scene["pcm"] = synthesize(scene["narration"], api_key)
            ok += 1
        except (requests.RequestException, ValueError, KeyError, wave.Error) as exc:
            failed += 1
            status = getattr(getattr(exc, "response", None), "status_code", None)
            print(f"tts_scene_failed scene={i} status={status} error={type(exc).__name__}", file=sys.stderr)
            if status in (400, 401, 403, 404, 429):
                stopped = True  # auth/quota/schema problems will not clear within this run
    print(f"tts_done ok={ok} failed={failed} silent={len(scenes) - ok}")


def scene_seconds(scene: dict) -> float:
    if scene["pcm"]:
        base = len(scene["pcm"]) / 2 / SAMPLE_RATE + GAP_SECONDS
    else:
        words = len(scene["narration"].split())
        base = max(MIN_SCENE_SECONDS, words / WORDS_PER_SECOND + GAP_SECONDS)
    return max(base, scene.get("min_seconds", 0.0))


# ---------------------------------------------------------------- output


def _ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def write_vtt(scenes: list[dict], path: Path) -> None:
    out, t = ["WEBVTT", ""], 0.0
    for scene in scenes:
        dur = scene_seconds(scene)
        out += [f"{_ts(t)} --> {_ts(t + dur - GAP_SECONDS)}", scene["narration"], ""]
        t += dur
    path.write_text("\n".join(out), encoding="utf-8")


def write_audio(scenes: list[dict], path: Path) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        for scene in scenes:
            frames = int(scene_seconds(scene) * SAMPLE_RATE)
            pcm = scene["pcm"][: frames * 2]
            w.writeframes(pcm + b"\x00\x00" * (frames - len(pcm) // 2))


def mux(scenes: list[dict], slides: list[Path], audio: Path, out: Path) -> None:
    listing = out.parent / "slides.txt"
    lines = []
    for scene, slide in zip(scenes, slides):
        lines += [f"file '{slide.name}'", f"duration {scene_seconds(scene):.3f}"]
    lines.append(f"file '{slides[-1].name}'")  # concat demuxer drops the last duration otherwise
    listing.write_text("\n".join(lines) + "\n", encoding="utf-8")
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(listing),
            "-i", str(audio),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "128k", "-shortest",
            "-movflags", "+faststart", str(out),
        ],
        check=True,
    )


def motion_minimum(scene: dict) -> float:
    """Floor so every card/stat finishes animating even for short narration."""
    kind = scene["kind"]
    if kind == "category":
        return 3.0 + SECONDS_PER_STORY * len(scene.get("stories", []))
    if kind == "stats":
        return 3.0 + 0.9 * len(scene.get("stats", []))
    if kind == "highlights":
        return 1.5 + 2.4 * len(scene.get("bullets", []))
    return 5.0


STORYBOARD_FIELDS = ("kicker", "heading", "bullets", "dek", "total", "stories", "stats")


def storyboard(recap: dict, scenes: list[dict]) -> dict:
    out = []
    for sc in scenes:
        item = {"type": sc["kind"], "seconds": round(scene_seconds(sc), 3)}
        item.update({k: sc[k] for k in STORYBOARD_FIELDS if k in sc})
        if sc["kind"] == "close":
            item["url"] = "llm-digest.com/daily"
        out.append(item)
    return {"date": recap["date"], "scenes": out}


def render_motion(sb_path: Path, audio: Path, out: Path, fps: int, scale: float) -> bool:
    """Render the animated video; False when node/playwright is unavailable."""
    node = shutil.which("node")
    if not node:
        print("motion_unavailable reason=missing_node fallback=slides", file=sys.stderr)
        return False
    proc = subprocess.run(
        [node, str(VIDEO_DIR / "render.mjs"), str(sb_path), str(out), "--audio", str(audio),
         "--fps", str(fps), "--scale", str(scale)]
    )
    if proc.returncode == 3:
        print("motion_unavailable reason=missing_playwright fallback=slides", file=sys.stderr)
        return False
    proc.check_returncode()
    return True


def build(date: str | None, out_root: Path, use_tts: bool, style: str = "motion", fps: int = 30, scale: float = 1.0) -> Path:
    if not shutil.which("ffmpeg"):
        raise SystemExit("video_build_skipped reason=missing_ffmpeg")
    recap = load_recap(date)
    date = recap["date"]
    out_dir = out_root / date
    out_dir.mkdir(parents=True, exist_ok=True)

    scenes = build_scenes(recap)
    if style == "motion":
        for sc in scenes:
            sc["min_seconds"] = motion_minimum(sc)
    narrate(scenes, os.environ.get("GEMINI_API_KEY") if use_tts else None)

    audio = out_dir / "narration.wav"
    write_audio(scenes, audio)
    write_vtt(scenes, out_dir / f"{date}.vtt")
    video = out_dir / f"{date}.mp4"
    rendered = False
    if style == "motion":
        sb_path = out_dir / "storyboard.json"
        sb_path.write_text(json.dumps(storyboard(recap, scenes), indent=2, ensure_ascii=False), encoding="utf-8")
        rendered = render_motion(sb_path, audio, video, fps, scale)
    if not rendered:
        if not og.fonts_available():
            raise SystemExit("video_build_skipped reason=missing_pillow_or_fonts")
        slides = []
        for i, scene in enumerate(scenes, 1):
            slide = out_dir / f"slide-{i:02d}.png"
            render_slide(scene, i, len(scenes), date).save(slide)
            slides.append(slide)
        mux(scenes, slides, audio, video)

    total = sum(scene_seconds(s) for s in scenes)
    meta = [{k: v for k, v in s.items() if k != "pcm"} | {"seconds": round(scene_seconds(s), 2), "voiced": bool(s["pcm"])} for s in scenes]
    (out_dir / "script.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"video_build_ok date={date} scenes={len(scenes)} seconds={total:.1f} path={video}")
    return video


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--date", help="recap date (default: latest.json)")
    ap.add_argument("--out", type=Path, default=OUT_ROOT)
    ap.add_argument("--style", choices=["motion", "slides"], default="motion",
                    help="motion: animated HTML player via Playwright (default); slides: static Pillow slides")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--scale", type=float, default=1.0, help="device scale factor: 1 = 720p, 1.5 = 1080p")
    ap.add_argument("--no-tts", action="store_true", help="skip narration; silent timed video")
    args = ap.parse_args()
    build(args.date, args.out, use_tts=not args.no_tts, style=args.style, fps=args.fps, scale=args.scale)


if __name__ == "__main__":
    main()
