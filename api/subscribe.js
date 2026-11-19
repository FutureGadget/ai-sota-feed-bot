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

// The send time an English signup asked for: 'us' (11:30 UTC) or the default
// 'kst' (23:00 UTC, the original send). Korean is always 'kst'.
export function subscribeSlot(value, locale = 'en') {
  return locale === 'en' && String(value || '').trim().toLowerCase() === 'us' ? 'us' : 'kst';
}

// The Resend segment for a language + send time, and every edition segment
// that is configured (so a switch can leave the others).
export function editionSegments(env = process.env) {
  const read = (name) => String(env[name] || '').trim();
  return {
    en: read('EMAIL_SEGMENT_ID') || read('EMAIL_AUDIENCE_ID'),
    ko: read('EMAIL_SEGMENT_ID_KO'),
    enUs: read('EMAIL_SEGMENT_ID_EN_US'),
  };
}

export function segmentFor(locale, slot, segments = editionSegments()) {
  if (locale === 'ko' && segments.ko) return segments.ko;
  if (locale === 'en' && slot === 'us' && segments.enUs) return segments.enUs;
  return segments.en;
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

// An existing subscriber who signs up again with another language or send
// time switches editions: join the requested edition's segment first, then
// leave the others, so a failure in between never leaves them with no edition.
export async function switchEdition(apiKey, email, targetSegment, otherSegments) {
  const contact = encodeURIComponent(email);
  const added = await withRateRetry(() =>
    resendCall(apiKey, 'POST', `/contacts/${contact}/segments/${encodeURIComponent(targetSegment)}`),
  );
  if (!added.ok && added.status !== 409 && added.status !== 422) {
    return { ok: false, step: 'add', status: added.status };
  }
  for (const other of [].concat(otherSegments || [])) {
    const removed = await withRateRetry(() =>
      resendCall(apiKey, 'DELETE', `/contacts/${contact}/segments/${encodeURIComponent(other)}`),
    );
    if (!removed.ok && removed.status !== 404) {
      return { ok: false, step: 'remove', status: removed.status };
    }
  }
  return { ok: true };
}

// Welcome email for a brand-new subscriber: what arrives and when, and one
// button to the latest brief. Sent once, only when the contact was just
// created, and best-effort: a failure never fails the signup. Needs EMAIL_FROM.
const WELCOME = {
  en: {
    subject: "You're in: welcome to LLM Digest",
    preheader: 'What arrives, when, and how to read it in five minutes.',
    kicker: 'Welcome',
    title: "You're in.",
    lead: 'LLM Digest is the AI brief for engineers who build and run AI systems: one shared ranking, no filter bubble, and it ends.',
    whatLabel: 'What you will get',
    daily: ['Daily brief', '{daily}. The day’s platform and agent news, ranked, deduped and grouped by theme. About five minutes.'],
    weekly: ['Weekly recap', '{weekly}. What happened this week, the storylines that moved, and what to read if you only read one thing.'],
    times: {
      kst: { daily: 'Every morning at 8:00 Seoul time (23:00 UTC)', weekly: 'Saturday at 8:00 Seoul time' },
      us: { daily: 'Every day at 11:30 UTC, early morning in New York', weekly: 'Saturday at 12:00 UTC' },
    },
    memory: ['Memory', 'Stories are followed across days, so each brief tells you what happened next.'],
    cta: "Read today's brief",
    ctaWeekly: "Read this week's recap",
    manage: 'Every email has a link at the bottom to switch to weekly only or unsubscribe.',
    tagline: 'The finishable AI feed for platform and agent engineers.',
  },
  ko: {
    subject: 'LLM Digest 구독을 환영합니다',
    preheader: '언제 무엇이 오는지, 5분 안에 읽는 법.',
    kicker: '환영합니다',
    title: '구독이 완료됐습니다.',
    lead: 'LLM Digest는 AI 시스템을 만들고 운영하는 엔지니어를 위한 브리프입니다. 모두에게 같은 랭킹, 필터 버블 없이, 끝이 있습니다.',
    whatLabel: '받게 될 메일',
    daily: ['데일리 브리프', '{daily}. 그날의 플랫폼·에이전트 소식을 랭킹하고 중복을 걸러 테마별로 묶었습니다. 약 5분.'],
    weekly: ['위클리 리캡', '{weekly}. 이번 주에 일어난 일과 움직인 스토리, 하나만 읽는다면 읽을 것.'],
    times: {
      kst: { daily: '매일 오전 8시(한국 시간)', weekly: '토요일 오전 8시' },
    },
    memory: ['맥락', '스토리를 날짜를 넘어 따라가서, 매 브리프가 그다음 소식을 알려 줍니다.'],
    cta: '오늘 브리프 읽기',
    ctaWeekly: '이번 주 리캡 읽기',
    manage: '모든 메일 하단의 링크에서 위클리만 받거나 수신을 거부할 수 있습니다.',
    tagline: '플랫폼·에이전트 엔지니어를 위한 끝이 있는 AI 피드.',
  },
};

const WELCOME_FONTS = "-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR','Segoe UI',Roboto,Helvetica,Arial,sans-serif";
const WELCOME_DARK_CSS =
  ':root{color-scheme:light dark;supported-color-schemes:light dark}' +
  '@media (prefers-color-scheme: dark){' +
  '.w-bg{background:#121417!important}.w-card{background:#1c2026!important;border-color:#30363d!important}' +
  '.w-text{color:#e6edf3!important}.w-soft{color:#c9d1d9!important}.w-muted{color:#8b949e!important}' +
  '.w-accent{color:#ff7b72!important}.w-rule{border-color:#30363d!important}' +
  '.w-btn{background:#e6edf3!important;color:#111111!important}}';

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}

export function welcomeEmail({ from, locale = 'en', weeklyOnly = false, slot = 'kst', siteBase = 'https://www.llm-digest.com' }) {
  const t = WELCOME[locale] || WELCOME.en;
  const when = t.times[slot] || t.times.kst;
  const fill = ([name, desc]) => [name, desc.replace('{daily}', when.daily).replace('{weekly}', when.weekly)];
  const base = siteBase.replace(/\/$/, '');
  const prefix = locale === 'ko' ? '/ko' : '';
  const latest = `${base}${prefix}${weeklyOnly ? '/weekly' : '/daily'}?utm_source=email&utm_medium=email&utm_campaign=welcome-${locale}`;
  const items = (weeklyOnly ? [t.weekly, t.memory] : [t.daily, t.weekly, t.memory]).map(fill);
  const cta = weeklyOnly ? t.ctaWeekly : t.cta;
  const keepAll = locale === 'ko' ? ';word-break:keep-all' : '';
  const rows = items
    .map(
      ([name, desc], i) =>
        `<tr><td class="w-rule" style="padding:14px 0;${i ? 'border-top:1px solid #e6e8eb;' : ''}">` +
        `<div class="w-text" style="font-size:17px;font-weight:700;line-height:1.35;color:#111">${escapeHtml(name)}</div>` +
        `<div class="w-soft" style="font-size:15px;line-height:1.55;color:#444;margin-top:3px">${escapeHtml(desc)}</div></td></tr>`,
    )
    .join('');
  const html =
    `<!DOCTYPE html><html lang="${locale}"><head><meta charset="utf-8">` +
    '<meta name="viewport" content="width=device-width, initial-scale=1">' +
    '<meta name="color-scheme" content="light dark"><meta name="supported-color-schemes" content="light dark">' +
    `<style>${WELCOME_DARK_CSS}</style></head>` +
    '<body class="w-bg" style="margin:0;padding:0;background:#f4f5f7">' +
    `<div style="display:none;max-height:0;overflow:hidden;opacity:0">${escapeHtml(t.preheader)}</div>` +
    `<div class="w-bg" lang="${locale}" style="background:#f4f5f7;padding:20px 12px;font-family:${WELCOME_FONTS}${keepAll}">` +
    '<div style="max-width:560px;margin:0 auto">' +
    `<div class="w-muted" style="font-size:13px;letter-spacing:.06em;text-transform:uppercase;color:#6e7781;margin:0 0 12px 4px">` +
    `<img src="${base}/logo.png" alt="" width="24" height="24" style="width:24px;height:24px;vertical-align:middle;margin-right:8px;border-radius:6px">LLM Digest</div>` +
    '<div class="w-card" style="background:#ffffff;border:1px solid #e6e8eb;border-radius:14px;padding:28px 24px">' +
    `<div class="w-accent" style="font-size:13px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#d1242f">${escapeHtml(t.kicker)}</div>` +
    `<h1 class="w-text" style="font-size:30px;line-height:1.2;margin:6px 0 12px;color:#111">${escapeHtml(t.title)}</h1>` +
    `<p class="w-soft" style="font-size:17px;line-height:1.6;color:#333;margin:0 0 22px">${escapeHtml(t.lead)}</p>` +
    `<div class="w-muted" style="font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#6e7781">${escapeHtml(t.whatLabel)}</div>` +
    `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:4px 0 22px">${rows}</table>` +
    `<a href="${escapeHtml(latest)}" class="w-btn" style="display:block;text-align:center;padding:14px 18px;border-radius:10px;background:#111;color:#ffffff;font-size:17px;font-weight:700;text-decoration:none">${escapeHtml(cta)} →</a>` +
    '</div>' +
    `<p class="w-muted" style="font-size:13px;line-height:1.6;color:#6e7781;margin:16px 4px 4px">${escapeHtml(t.manage)}</p>` +
    `<p class="w-muted" style="font-size:13px;line-height:1.6;color:#6e7781;margin:0 4px">${escapeHtml(t.tagline)} · <a href="${base}${prefix}/" class="w-muted" style="color:#6e7781;white-space:nowrap">llm-digest.com</a></p>` +
    '</div></div></body></html>';
  const text = [
    t.title,
    '',
    t.lead,
    '',
    ...items.map(([name, desc]) => `${name}: ${desc}`),
    '',
    `${cta}: ${latest}`,
    '',
    t.manage,
  ].join('\n');
  return { from, to: [], subject: t.subject, html, text };
}

async function sendWelcome(apiKey, email, locale, weeklyOnly, slot = 'kst') {
  const from = String(process.env.EMAIL_FROM || '').trim();
  if (!from) return;
  const payload = welcomeEmail({
    from,
    locale,
    weeklyOnly,
    slot,
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
  // Send time: English readers who chose the US-morning send go to
  // EMAIL_SEGMENT_ID_EN_US when it is configured; everyone else keeps the
  // original 23:00 UTC send.
  const locale = subscribeLocale(body.locale);
  const segments = editionSegments();
  const slot = segments.enUs ? subscribeSlot(body.send_time, locale) : 'kst';
  const segmentId = segmentFor(locale, slot, segments);
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
      await sendWelcome(apiKey, email, locale, weeklyOnly, slot);
      return Response.json({ ok: true });
    }
    // 409/422 typically means the contact already exists — a re-subscribe is
    // success (idempotent). When both language editions are configured, it
    // also moves the contact to the edition this signup asked for.
    if (r.status === 409 || r.status === 422) {
      const others = [...new Set([segments.en, segments.ko, segments.enUs].filter((id) => id && id !== segmentId))];
      if (segmentId && others.length) {
        const moved = await switchEdition(apiKey, email, segmentId, others);
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
