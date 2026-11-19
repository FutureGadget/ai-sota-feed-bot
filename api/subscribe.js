// POST /api/subscribe { email, hp? } — registers a self-serve subscriber by
// adding them to your Resend contacts.
//
// Resend's contacts are global (created at POST /contacts). The API key alone
// is required, but we also add the contact to EMAIL_SEGMENT_ID (the segment the
// daily/weekly broadcast sends to) via the `segments` array — otherwise the
// contact is created segment-less and the broadcast fails with 422 "...has no
// contacts". Per-digest selection rides on Resend Topics: EMAIL_TOPIC_ID_DAILY
// and EMAIL_TOPIC_ID_WEEKLY are separate topics, so a "weekly only" signup opts
// the contact OUT of the daily topic while staying in the weekly one (Resend's
// preference page then manages it). Falls back to a single legacy EMAIL_TOPIC_ID.
//
// The key is read server-side only (never reaches the browser). Honeypot +
// validation guard abuse. With no EMAIL_API_KEY the endpoint returns 503 and
// the client hides the form.

import { follow, page, unfollow, watch } from '../lib/follow.js';
import { readerIdFor } from '../lib/reader-id.js';

export { readerIdFor };

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// The email edition a signup asked for: 'ko' or the default 'en'.
export function subscribeLocale(value) {
  return String(value || '').trim().toLowerCase() === 'ko' ? 'ko' : 'en';
}
function resendCall(apiKey, method, path, payload) {
  return fetch(`https://api.resend.com${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: payload === undefined ? undefined : JSON.stringify(payload),
  });
}

// Resend allows a few requests per second; a language switch makes up to four.
async function withRateRetry(call) {
  const r = await call();
  if (r.status !== 429) return r;
  await new Promise((resolve) => setTimeout(resolve, 1100));
  return call();
}

// An existing subscriber who signs up again with the other language switches
// editions: join the requested edition's segment first, then leave the other,
// so a failure in between never leaves them with no edition.
export async function switchEdition(apiKey, email, targetSegment, otherSegment) {
  const contact = encodeURIComponent(email);
  const added = await withRateRetry(() =>
    resendCall(apiKey, 'POST', `/contacts/${contact}/segments/${encodeURIComponent(targetSegment)}`),
  );
  if (!added.ok && added.status !== 409 && added.status !== 422) {
    return { ok: false, step: 'add', status: added.status };
  }
  const removed = await withRateRetry(() =>
    resendCall(apiKey, 'DELETE', `/contacts/${contact}/segments/${encodeURIComponent(otherSegment)}`),
  );
  if (!removed.ok && removed.status !== 404) {
    return { ok: false, step: 'remove', status: removed.status };
  }
  return { ok: true };
}

// Welcome email for a brand-new subscriber: what arrives and when, a link to
// the latest brief, and a nudge to add the sender to contacts. Sent once, only
// when the contact was just created, and best-effort: a failure never fails
// the signup. Needs EMAIL_FROM; EMAIL_REPLY_TO is optional.
const WELCOME = {
  en: {
    subject: 'Welcome to LLM Digest',
    hello: "You're subscribed. Thanks for signing up.",
    daily: 'The daily brief arrives every morning, and the weekly recap on Saturdays.',
    weekly: 'The weekly recap arrives every Saturday morning.',
    finish: 'Each one ends: read it and you are caught up.',
    latest: "Read today's brief now",
    contacts: (from) => `So the next one lands in your inbox, add ${from} to your contacts.`,
    reply: 'Reply to this email any time; replies reach a person.',
    manage: 'Every digest has a link to change what you get or unsubscribe.',
  },
  ko: {
    subject: 'LLM Digest 구독을 환영합니다',
    hello: '구독이 완료되었습니다. 신청해 주셔서 감사합니다.',
    daily: '데일리 브리프는 매일 오전 8시(한국 시간)에, 위클리 리캡은 토요일 오전 8시에 도착합니다.',
    weekly: '위클리 리캡이 매주 토요일 오전 8시(한국 시간)에 도착합니다.',
    finish: '끝이 있는 브리프입니다. 다 읽으면 따라잡기 끝.',
    latest: '오늘 브리프 바로 읽기',
    contacts: (from) => `다음 메일이 받은편지함에 잘 도착하도록 ${from}을 연락처에 추가해 주세요.`,
    reply: '언제든 이 메일에 답장하시면 사람이 직접 읽습니다.',
    manage: '모든 다이제스트 하단의 링크에서 받는 메일을 바꾸거나 수신을 거부할 수 있습니다.',
  },
};

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}

export function welcomeEmail({ from, replyTo = '', locale = 'en', weeklyOnly = false, siteBase = 'https://www.llm-digest.com' }) {
  const t = WELCOME[locale] || WELCOME.en;
  const base = siteBase.replace(/\/$/, '');
  const prefix = locale === 'ko' ? '/ko' : '';
  const latest = `${base}${prefix}${weeklyOnly ? '/weekly' : '/daily'}?utm_source=email&utm_medium=email&utm_campaign=welcome-${locale}`;
  const address = (String(from).match(/<([^>]+)>/) || [null, from])[1];
  const lines = [t.hello, weeklyOnly ? t.weekly : t.daily, t.finish];
  const extra = [t.contacts(address), replyTo ? t.reply : '', t.manage].filter(Boolean);
  const html = [
    `<div lang="${locale}" style="max-width:560px;margin:0 auto;padding:24px 18px;font-family:-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR','Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#111;font-size:16px;line-height:1.6${locale === 'ko' ? ';word-break:keep-all' : ''}">`,
    `<h1 style="font-size:22px;margin:0 0 12px">${escapeHtml(t.subject)}</h1>`,
    ...lines.map((line) => `<p style="margin:0 0 10px">${escapeHtml(line)}</p>`),
    `<p style="margin:18px 0"><a href="${escapeHtml(latest)}" style="display:inline-block;padding:10px 16px;border-radius:8px;background:#1a6dd6;color:#fff;text-decoration:none;font-weight:600">${escapeHtml(t.latest)} →</a></p>`,
    ...extra.map((line) => `<p style="margin:0 0 8px;font-size:14px;color:#555">${escapeHtml(line)}</p>`),
    '</div>',
  ].join('');
  const text = [...lines, '', `${t.latest}: ${latest}`, '', ...extra].join('\n');
  const payload = { from, to: [], subject: t.subject, html, text };
  if (replyTo) payload.reply_to = replyTo;
  return payload;
}

async function sendWelcome(apiKey, email, locale, weeklyOnly) {
  const from = String(process.env.EMAIL_FROM || '').trim();
  if (!from) return;
  const payload = welcomeEmail({
    from,
    replyTo: String(process.env.EMAIL_REPLY_TO || '').trim(),
    locale,
    weeklyOnly,
    siteBase: String(process.env.SITE_BASE_URL || 'https://www.llm-digest.com'),
  });
  payload.to = [email];
  try {
    const r = await resendCall(apiKey, 'POST', '/emails', payload);
    if (!r.ok) console.error('resend welcome failed', r.status);
  } catch (e) {
    console.error('resend welcome failed', String(e).slice(0, 200));
  }
}

function createContact(apiKey, payload) {
  return fetch('https://api.resend.com/contacts', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
}

// GET /api/subscribe?c=&s=&t= is a signed storyline unfollow link
// (lib/follow.js); plain GETs have nothing to serve.
export async function GET(request) {
  const apiKey = String(process.env.EMAIL_API_KEY || '').trim();
  if (!apiKey) return page('Unavailable', 'Story follow emails are not configured.', 503);
  return unfollow(new URL(request.url), apiKey);
}

export async function POST(request) {

  const apiKey = String(process.env.EMAIL_API_KEY || '').trim();
  const url = new URL(request.url);
  // One-click unsubscribe (RFC 8058) posts to the List-Unsubscribe URL.
  if (url.searchParams.has('t')) {
    if (!apiKey) return page('Unavailable', 'Story follow emails are not configured.', 503);
    return unfollow(url, apiKey);
  }
  if (!apiKey) {
    return Response.json({ error: 'not_configured' }, { status: 503 });
  }

  let body;
  try {
    body = await request.json();
  } catch {
    body = {};
  }
  body = body || {};
  if (body.action === 'follow') return follow(body, apiKey);
  if (body.action === 'watch') return watch(body, apiKey);

  // Honeypot: a real user leaves this empty; bots fill every field. Report
  // success without touching the provider so the bot learns nothing.
  if (String(body.hp || body.website || '').trim()) {
    return Response.json({ ok: true });
  }

  const email = String(body.email || '').trim().toLowerCase();
  if (!EMAIL_RE.test(email) || email.length > 254) {
    return Response.json({ error: 'invalid_email' }, { status: 400 });
  }

  const payload = { email, unsubscribed: false, properties: { reader_id: readerIdFor(body.reader_id) } };
  // Per-digest selection. Daily and weekly are separate Resend Topics so a reader
  // can take "weekly only — less email": opted into the weekly topic, opted OUT
  // of the daily one (Resend then suppresses the daily broadcast for them, and
  // its hosted preference page manages the choice thereafter). Default = both.
  // Falls back to the legacy single EMAIL_TOPIC_ID (both digests, one topic)
  // when the per-kind ids aren't configured.
  const dailyTopic = String(process.env.EMAIL_TOPIC_ID_DAILY || '').trim();
  const weeklyTopic = String(process.env.EMAIL_TOPIC_ID_WEEKLY || '').trim();
  const weeklyOnly = body.weekly_only === true || String(body.weekly_only || '') === 'true';
  const topics = [];
  if (dailyTopic) topics.push({ id: dailyTopic, subscription: weeklyOnly ? 'opt_out' : 'opt_in' });
  if (weeklyTopic) topics.push({ id: weeklyTopic, subscription: 'opt_in' });
  if (!topics.length) {
    const legacyTopic = String(process.env.EMAIL_TOPIC_ID || '').trim();
    if (legacyTopic) topics.push({ id: legacyTopic, subscription: 'opt_in' });
  }
  if (topics.length) payload.topics = topics;
  // Place the contact into the segment the daily/weekly broadcast targets
  // (publish_email.py sends to EMAIL_SEGMENT_ID). Without this the contact is
  // created segment-less and a broadcast to that segment fails with
  // 422 "...has no contacts". Mirror the broadcast's env resolution exactly.
  // Language edition: Korean readers go to EMAIL_SEGMENT_ID_KO, which the
  // Korean broadcast targets; everyone else (and Korean readers when that
  // segment is not configured) to the English segment.
  const locale = subscribeLocale(body.locale);
  const englishSegment = String(process.env.EMAIL_SEGMENT_ID || process.env.EMAIL_AUDIENCE_ID || '').trim();
  const koreanSegment = String(process.env.EMAIL_SEGMENT_ID_KO || '').trim();
  const segmentId = locale === 'ko' && koreanSegment ? koreanSegment : englishSegment;
  if (segmentId) payload.segments = [{ id: segmentId }];

  try {
    let r = await createContact(apiKey, payload);
    // A 422 can mean "already a contact" or a rejected custom property (e.g. the
    // `reader_id` property isn't defined yet). Retry once without properties so
    // attribution can never cost a signup; a duplicate stays a 409/422.
    if (r.status === 422) {
      const { properties, ...withoutProperties } = payload;
      r = await createContact(apiKey, withoutProperties);
    }

    if (r.ok) {
      await sendWelcome(apiKey, email, locale, weeklyOnly);
      return Response.json({ ok: true });
    }
    // 409/422 typically means the contact already exists — a re-subscribe is
    // success (idempotent). When both language editions are configured, it
    // also moves the contact to the edition this signup asked for.
    if (r.status === 409 || r.status === 422) {
      if (englishSegment && koreanSegment && englishSegment !== koreanSegment) {
        const other = segmentId === koreanSegment ? englishSegment : koreanSegment;
        const moved = await switchEdition(apiKey, email, segmentId, other);
        if (!moved.ok) {
          console.error('resend edition switch failed', moved.step, moved.status);
          return Response.json({ error: 'provider_error', status: moved.status }, { status: 502 });
        }
      }
      return Response.json({ ok: true });
    }
    const detail = await r.text().catch(() => '');
    // Surface the upstream status in the Vercel function logs — the usual cause
    // is a "Sending access" API key that can't write contacts (needs Full access).
    console.error('resend create-contact failed', r.status, detail.slice(0, 300));
    return Response.json(
      { error: 'provider_error', status: r.status, detail: detail.slice(0, 200) },
      { status: 502 }
    );
  } catch (e) {
    return Response.json(
      { error: 'provider_unreachable', detail: String(e).slice(0, 200) },
      { status: 502 }
    );
  }
}
