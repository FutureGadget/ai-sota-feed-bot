// Pseudonymous reader id stored on a Resend contact as the `reader_id`
// property. Broadcasts template it into every link as `rid=` so email clicks
// keep the subscriber's identity (publish/publish_email.py::tag_reader_links).
// The signup browser's own anonymous id is reused when valid, so its history
// and its future email clicks count as one reader; otherwise one is minted.
const READER_ID_RE = /^anon_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

export function readerIdFor(candidate) {
  const value = String(candidate || '').trim().toLowerCase();
  return READER_ID_RE.test(value) ? value : `anon_${crypto.randomUUID()}`;
}
