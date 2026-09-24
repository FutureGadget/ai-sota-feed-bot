#!/usr/bin/env python3
"""One-off: give every existing Resend contact a ``reader_id`` property.

New signups get one from ``api/subscribe.js``; contacts created before that
have none, so their email links would carry the ``none`` fallback and their
visits would stay unattributed. Safe to re-run: contacts that already have a
``reader_id`` are left untouched.

Usage:
    EMAIL_API_KEY=re_... python3 publish/backfill_reader_ids.py --dry-run
    EMAIL_API_KEY=re_... python3 publish/backfill_reader_ids.py
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from publish.publish_email import READER_ID_PROPERTY, ensure_reader_id_property  # noqa: E402

API = "https://api.resend.com"


def new_reader_id() -> str:
    # Same shape as the browser's anonymous id (web/posthog-client.js), which
    # is the format the client accepts from `?rid=`.
    return f"anon_{uuid.uuid4()}"


def existing_reader_id(contact: dict) -> str:
    prop = (contact.get("properties") or {}).get(READER_ID_PROPERTY)
    value = prop.get("value") if isinstance(prop, dict) else prop
    return str(value or "").strip()


def list_contact_ids(headers: dict) -> list[str]:
    ids: list[str] = []
    after = None
    while True:
        params = {"limit": 100}
        if after:
            params["after"] = after
        r = requests.get(f"{API}/contacts", headers=headers, params=params, timeout=30)
        r.raise_for_status()
        payload = r.json()
        rows = payload.get("data") or []
        ids.extend(str(c["id"]) for c in rows if c.get("id"))
        if not payload.get("has_more") or not rows:
            return ids
        after = rows[-1]["id"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="report what would change, write nothing")
    args = ap.parse_args()

    api_key = os.getenv("EMAIL_API_KEY", "").strip()
    if not api_key:
        print("reader_id_backfill_skipped=true reason=no_api_key")
        return 0
    headers = {"Authorization": f"Bearer {api_key}"}

    if not args.dry_run and not ensure_reader_id_property(api_key):
        print("reader_id_backfill_failed=true reason=property_unavailable")
        return 1

    updated = skipped = 0
    for contact_id in list_contact_ids(headers):
        time.sleep(0.6)  # Resend's default limit is 2 requests/second
        r = requests.get(f"{API}/contacts/{contact_id}", headers=headers, timeout=30)
        r.raise_for_status()
        if existing_reader_id(r.json()):
            skipped += 1
            continue
        if not args.dry_run:
            r = requests.patch(
                f"{API}/contacts/{contact_id}",
                headers=headers,
                json={"properties": {READER_ID_PROPERTY: new_reader_id()}},
                timeout=30,
            )
            r.raise_for_status()
            time.sleep(0.6)
        updated += 1

    print(f"reader_id_backfill_done=true dry_run={str(args.dry_run).lower()} updated={updated} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
