#!/usr/bin/env python3
"""Upload one MP4 to YouTube (resumable). Prints {"id","url","privacy"} JSON.

Usage: youtube_upload.py FILE --title T --description D [--privacy unlisted]

Auth: requests carry no credentials; the cloud agent proxy attaches the OAuth
2.0 authorization. For local testing only, ~/.youtube-client-secret.json +
~/.youtube-refresh-token are exchanged for an access token when both exist.
Nothing secret is ever printed.
"""
import argparse, json, os, sys, urllib.error, urllib.parse, urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("file"); ap.add_argument("--title", required=True)
ap.add_argument("--description", default="")
ap.add_argument("--privacy", default="unlisted", choices=["private", "unlisted", "public"])
a = ap.parse_args()

def local_access_token():  # local testing only
    cs, rt = (os.path.expanduser(p) for p in ("~/.youtube-client-secret.json", "~/.youtube-refresh-token"))
    if not (os.path.exists(cs) and os.path.exists(rt)):
        return None
    c = json.load(open(cs))["installed"]
    body = urllib.parse.urlencode({"client_id": c["client_id"], "client_secret": c["client_secret"],
                                   "refresh_token": open(rt).read().strip(), "grant_type": "refresh_token"}).encode()
    try:
        return json.load(urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", body)))["access_token"]
    except urllib.error.HTTPError as e:
        sys.exit(f"token exchange failed: HTTP {e.code}")

hdr = {}
_tok = local_access_token()
if _tok:
    hdr["Authorization"] = "Bearer " + _tok

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
