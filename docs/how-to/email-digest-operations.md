# Email digest — go-live & operations

How to turn on, verify, and operate the email digest (Resend). Spec:
`docs/product-specs/email-digest.md`; plan: `docs/exec-plans/active/v2.2-email-digest.md`.

## Configuration (where each var lives)

| Var | Where | Type | Needed for |
|---|---|---|---|
| `EMAIL_API_KEY` | Vercel **and** GitHub Actions | Vercel env / GH **Secret** | signup + send |
| `EMAIL_SEGMENT_ID` | GitHub Actions | **Secret** | send only (broadcast target) |
| `EMAIL_FROM` | GitHub Actions | **Variable** (`vars.`) | send only — e.g. `LLM Digest <digest@llm-digest.com>` |
| `EMAIL_TOPIC_ID` | GitHub Actions (optional) | Secret | per-topic unsubscribe |

Plus `config/email.yaml → enabled: true` (the second send gate) and a **verified
domain** in Resend for the `EMAIL_FROM` address.

Registration needs only `EMAIL_API_KEY` (Resend contacts are global). A
segment id is a *send-time* concern, so signup and sending are decoupled.

## Go-live sequence

1. Verify the `EMAIL_FROM` domain in Resend (SPF/DKIM/DMARC records → "Verified").
2. Set the env vars above; `config/email.yaml → enabled: true`.
3. **Merge to main** — production Vercel deploy makes the signup form live, and
   the scheduled send runs from main.
4. **Redeploy Vercel** if the env vars were added after the last deploy (env
   changes only apply to new deployments).
5. Verify signup (below), then a `dry_run` send, then a real send.

## Verify signup

After the deploy carries `EMAIL_API_KEY`:

```bash
curl -i -X POST https://www.llm-digest.com/api/subscribe \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@yourdomain.com"}'
```

- `200 {"ok":true}` → the address appears in Resend → Contacts. ✅
- `503 {"error":"not_configured"}` → `EMAIL_API_KEY` not on the deploy → redeploy.
- `400 {"error":"invalid_email"}` → malformed address.

Or use the 🔔 menu on the site (the inline email form renders when the key is set).

## Verify sending

Actions → **AI Feed Email Digest** → **Run workflow**:

1. `dry_run: true` — renders the HTML into the job log, **sends nothing, touches
   no cursor**. Eyeball it.
2. `dry_run: false` — real broadcast to the segment. Subscribe your own address
   first so there's a recipient; check your inbox + the unsubscribe link.

Greppable run signals from `publish/publish_email.py`:
`email_sent=true` / `email_skipped=true reason=…` / `email_send_skipped=true reason=disabled_or_no_api_key`.

## Cadence

- Daily brief: `30 22 * * *` (07:30 KST).
- Weekly recap: `0 23 * * 5` (Fri 23:00 UTC) — mapped to `--kind weekly` via
  `github.event.schedule`.

Both read whatever the hourly pipeline already committed; they never run on the
hourly schedule.

## Troubleshooting

- **No-op despite env set** → `config/email.yaml` still `enabled: false`, or the
  change isn't on main yet (the cron runs from main).
- **`resend requires EMAIL_SEGMENT_ID and EMAIL_FROM`** → add the missing send
  var (segment as a Secret, from as a Variable).
- **Mail in spam** → domain not fully verified, or new-domain reputation; our
  bodies already include Resend's `{{{RESEND_UNSUBSCRIBE_URL}}}` token.
- **Same-day re-run sends nothing** → `data/email/state.json` guard
  (`last_sent_date` / `last_sent_week`); use the `--force` CLI flag to override.
