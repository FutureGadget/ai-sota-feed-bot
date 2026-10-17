#!/usr/bin/env python3
"""Upload one MP4 to YouTube (resumable). Prints {"id","url","privacy"} JSON.

Usage: youtube_upload.py FILE --title T --description D [--privacy unlisted]

Auth (environment variables, first match wins; values are never printed):
  1. YOUTUBE_CLIENT_ID + YOUTUBE_CLIENT_SECRET + YOUTUBE_REFRESH_TOKEN: a fresh
     access token is minted on every run, so nothing expires.
  2. YOUTUBE_ACCESS_TOKEN: used as-is (valid for one hour; for quick tests).
Required scope: https://www.googleapis.com/auth/youtube.upload
"""
import argparse, json, os, sys, urllib.error, urllib.parse, urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("file"); ap.add_argument("--title", required=True)
ap.add_argument("--description", default="")
ap.add_argument("--privacy", default="unlisted", choices=["private", "unlisted", "public"])
a = ap.parse_args()

def auth_headers():
    e = os.environ
    if e.get("YOUTUBE_CLIENT_ID") and e.get("YOUTUBE_CLIENT_SECRET") and e.get("YOUTUBE_REFRESH_TOKEN"):
        body = urllib.parse.urlencode({"client_id": e["YOUTUBE_CLIENT_ID"], "client_secret": e["YOUTUBE_CLIENT_SECRET"],
                                       "refresh_token": e["YOUTUBE_REFRESH_TOKEN"], "grant_type": "refresh_token"}).encode()
        try:
            tok = json.load(urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", body)))["access_token"]
        except urllib.error.HTTPError as err:
            sys.exit(f"token refresh failed: HTTP {err.code} {err.read()[:300].decode()}")
        return {"Authorization": "Bearer " + tok}
    if e.get("YOUTUBE_ACCESS_TOKEN"):
        return {"Authorization": "Bearer " + e["YOUTUBE_ACCESS_TOKEN"]}
    sys.exit("no YouTube credentials: set YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET and YOUTUBE_REFRESH_TOKEN")

hdr = auth_headers()

def fail(e):
    sys.exit(f"HTTP {e.code} {e.read()[:600].decode()}")

size = os.path.getsize(a.file)
meta = {"snippet": {"title": a.title[:100], "description": a.description[:4900], "categoryId": "28"},
        "status": {"privacyStatus": a.privacy, "selfDeclaredMadeForKids": False}}
init = urllib.request.Request(
    "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
    json.dumps(meta).encode(),
    {**hdr, "Content-Type": "application/json; charset=UTF-8", "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)})
try:
    loc = urllib.request.urlopen(init).headers["Location"]
except urllib.error.HTTPError as e:
    fail(e)
with open(a.file, "rb") as f:
    put = urllib.request.Request(loc, f.read(), {**hdr, "Content-Type": "video/mp4"}, method="PUT")
try:
    r = json.load(urllib.request.urlopen(put, timeout=900))
except urllib.error.HTTPError as e:
    fail(e)
print(json.dumps({"id": r["id"], "url": "https://youtu.be/" + r["id"], "privacy": r["status"]["privacyStatus"]}))
