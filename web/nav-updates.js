/* "New updates" indicators — shared by every shell and the generated static
 * pages (see docs/product-specs/nav-update-indicators.md).
 *
 * Two surfaces, one signal:
 *  1. Nav "New" pills on the Editor's Desk links for sections with unread,
 *     still-fresh editorial content (rolled up onto the Desk trigger by
 *     site-chrome.js).
 *  2. A one-line "Fresh from the Editor's Desk" strip at the top of the live
 *     feed, naming the unread sections as directly clickable chips. It only
 *     renders for returning readers (a section must have been visited before
 *     — i.e. have a "seen" marker — so it never nags about sections the
 *     reader has not engaged with) and disappears entirely when caught up.
 *
 * Signals come from /api/updates; "seen" markers live in localStorage and are
 * recorded when the reader is on a section's page. Everything is defensive:
 * a failed fetch or blocked storage must never affect the page.
 */
(function () {
  var SEEN = {
    daily: 'ai_feed_seen_daily_v1',
    weekly: 'ai_feed_seen_weekly_v1',
    storylines: 'ai_feed_seen_storylines_v1',
    playbook: 'ai_feed_seen_playbook_v1',
    map: 'ai_feed_seen_map_v1',
    foundations: 'ai_feed_seen_foundations_v1'
  };
  var ROUTE = {
    '/daily': 'daily',
    '/weekly': 'weekly',
    '/storylines': 'storylines',
    '/playbook': 'playbook',
    '/map': 'map',
    '/foundations': 'foundations'
  };
  var STRIP_DISMISS_KEY = 'ai_feed_whats_new_dismissed_v1'; // sessionStorage
  // Daily/weekly/playbook age-out: stale editions are not "fresh" even when unread.
  var DAILY_FRESH_MAX_AGE = 1;   // covers today or yesterday
  var WEEKLY_FRESH_MAX_AGE = 8;  // most recent completed week (+1 day grace)
  var PLAYBOOK_FRESH_MAX_AGE = 10; // editions are curated every few days

  function getItem(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function setItem(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function ms(s) { var t = s ? Date.parse(s) : NaN; return isFinite(t) ? t : NaN; }

  function currentSection() {
    var p = location.pathname.replace(/\/+$/, '') || '/';
    if (p === '/daily' || p.indexOf('/daily/') === 0) return 'daily';
    if (p === '/weekly' || p.indexOf('/weekly/') === 0) return 'weekly';
    if (p === '/storylines' || p.indexOf('/storyline/') === 0) return 'storylines';
    if (p === '/playbook' || p.indexOf('/playbook/') === 0) return 'playbook';
    if (p === '/map' || p.indexOf('/topic/') === 0) return 'map';
    if (p === '/foundations' || p.indexOf('/foundations/') === 0) return 'foundations';
    return null;
  }

  function isFeedPage() {
    return (location.pathname.replace(/\/+$/, '') || '/') === '/';
  }

  // Whole-day difference (now - dateStr), UTC, in days.
  function dayAge(nowIso, dateStr) {
    if (!dateStr) return Infinity;
    var now = new Date(nowIso);
    var d = new Date(dateStr.length === 10 ? dateStr + 'T00:00:00Z' : dateStr);
    if (isNaN(now.getTime()) || isNaN(d.getTime())) return Infinity;
    var a = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
    var b = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
    return Math.round((a - b) / 86400000);
  }

  // Value compared against the "seen" marker for each section.
  function signalOf(u, section) {
    if (section === 'daily') return u.daily && u.daily.generated_at;
    if (section === 'weekly') return u.weekly && u.weekly.generated_at;
    if (section === 'storylines') return u.storylines && u.storylines.last_updated;
    if (section === 'playbook') return u.playbook && u.playbook.generated_at;
    if (section === 'map') return u.map && u.map.updated;
    if (section === 'foundations') return u.foundations && u.foundations.updated;
    return null;
  }

  function isUnread(section, signal) {
    var seen = getItem(SEEN[section]);
    if (!seen) return true;
    var a = ms(signal), b = ms(seen);
    if (isFinite(a) && isFinite(b)) return a > b;
    return String(signal) > String(seen); // date-only strings sort lexically
  }

  function isFresh(section, u) {
    if (section === 'daily') return dayAge(u.now, u.daily && u.daily.date) <= DAILY_FRESH_MAX_AGE;
    if (section === 'weekly') return dayAge(u.now, u.weekly && u.weekly.end) <= WEEKLY_FRESH_MAX_AGE;
    if (section === 'playbook') return dayAge(u.now, u.playbook && u.playbook.date) <= PLAYBOOK_FRESH_MAX_AGE;
    return true; // storylines + map + foundations: read history only, no time gate
  }

  function injectStyle() {
    if (document.getElementById('nav-update-style')) return;
    var s = document.createElement('style');
    s.id = 'nav-update-style';
    s.textContent = '.nav-update-dot{display:inline-block;margin-left:.4rem;padding:.03rem .34rem;font-size:.62rem;font-weight:700;line-height:1.5;letter-spacing:.04em;text-transform:uppercase;color:var(--accent,#2563eb);background:color-mix(in srgb,var(--accent,#2563eb) 16%,transparent);border:1px solid color-mix(in srgb,var(--accent,#2563eb) 38%,transparent);border-radius:999px;vertical-align:middle;animation:navUpdateIn .35s ease-out both}@keyframes navUpdateIn{from{opacity:0;transform:scale(.7)}to{opacity:1;transform:scale(1)}}@media (prefers-reduced-motion:reduce){.nav-update-dot{animation:none}}.nav-update-sr{position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}';
    (document.head || document.documentElement).appendChild(s);
  }

  function injectStripStyle() {
    if (document.getElementById('whats-new-style')) return;
    var s = document.createElement('style');
    s.id = 'whats-new-style';
    s.textContent = '.whats-new{display:flex;flex-wrap:wrap;align-items:center;gap:.4rem .5rem;margin:0 0 1rem;padding:.55rem .55rem .55rem .8rem;border:1px solid color-mix(in srgb,var(--accent,#2563eb) 20%,transparent);border-left:3px solid var(--accent,#2563eb);border-radius:10px;background:color-mix(in srgb,var(--accent,#2563eb) 6%,transparent);font-size:.85rem;animation:navUpdateIn .35s ease-out both}@media (prefers-reduced-motion:reduce){.whats-new{animation:none}}.whats-new-label{font-weight:600;opacity:.85;margin-right:.15rem}.whats-new-chip{display:inline-block;padding:.12rem .6rem;font-size:.8rem;font-weight:600;line-height:1.5;color:var(--accent,#2563eb);background:color-mix(in srgb,var(--accent,#2563eb) 13%,transparent);border:1px solid color-mix(in srgb,var(--accent,#2563eb) 34%,transparent);border-radius:999px;text-decoration:none;white-space:nowrap}.whats-new-chip:hover{background:color-mix(in srgb,var(--accent,#2563eb) 24%,transparent);text-decoration:none}.whats-new-dismiss{margin-left:auto;padding:0 .35rem;border:0;background:none;color:inherit;opacity:.55;font-size:1rem;line-height:1;cursor:pointer}.whats-new-dismiss:hover{opacity:1}';
    (document.head || document.documentElement).appendChild(s);
  }

  function decorate(section) {
    var links = document.querySelectorAll('.site-nav-fallback a[href]');
    for (var i = 0; i < links.length; i++) {
      var a = links[i];
      var pathOnly = (a.getAttribute('href') || '').split('#')[0].split('?')[0].replace(/\/+$/, '');
      if (ROUTE[pathOnly] !== section || a.querySelector('.nav-update-dot')) continue;
      // Give the link a containing block: the sr-only label below is
      // position:absolute and would otherwise escape the nav's overflow clip
      // and open a phantom horizontal scroll gutter on mobile.
      if (window.getComputedStyle(a).position === 'static') a.style.position = 'relative';
      var dot = document.createElement('span');
      dot.className = 'nav-update-dot';
      dot.textContent = 'New';
      dot.setAttribute('aria-hidden', 'true');
      a.appendChild(dot);
      var sr = document.createElement('span');
      sr.className = 'nav-update-sr';
      sr.textContent = ' (new updates)';
      a.appendChild(sr);
    }
  }

  function capture(event, props) {
    try {
      if (window.aiFeedPostHog && window.aiFeedPostHog.capture) window.aiFeedPostHog.capture(event, props);
      else if (window.posthog && window.posthog.capture) window.posthog.capture(event, props);
    } catch (e) {}
  }

  // Chip label per section — daily gets a day-aware label so the chip itself
  // says what's waiting ("Today's recap" beats a bare "Daily").
  function stripLabel(section, u) {
    if (section === 'daily') {
      return dayAge(u.now, u.daily && u.daily.date) <= 0 ? "Today's recap" : "Yesterday's recap";
    }
    if (section === 'weekly') return 'Weekly recap';
    if (section === 'storylines') return 'Storylines';
    if (section === 'playbook') return 'Playbook';
    if (section === 'map') return 'Agent know-how';
    if (section === 'foundations') return 'Foundations';
    return section;
  }

  var STRIP_HREF = {
    daily: '/daily',
    weekly: '/weekly',
    storylines: '/storylines',
    playbook: '/playbook',
    map: '/map',
    foundations: '/foundations'
  };

  function isStripDismissed() {
    try { return sessionStorage.getItem(STRIP_DISMISS_KEY) === '1'; } catch (e) { return false; }
  }

  function renderStrip(u, sections) {
    var anchor = document.getElementById('list');
    var parent = anchor && anchor.parentNode;
    if (!parent) return [];
    injectStripStyle();

    var strip = document.createElement('section');
    strip.className = 'whats-new';
    strip.setAttribute('aria-label', 'New editorial updates since your last visit');

    var label = document.createElement('span');
    label.className = 'whats-new-label';
    label.textContent = '🗞️ Fresh from the Editor’s Desk:';
    strip.appendChild(label);

    sections.forEach(function (section) {
      var a = document.createElement('a');
      a.className = 'whats-new-chip';
      a.href = STRIP_HREF[section];
      a.textContent = stripLabel(section, u);
      a.setAttribute('data-whats-new', section);
      a.addEventListener('click', function () {
        capture('whats_new_click', { section: section });
      });
      strip.appendChild(a);
    });

    var dismiss = document.createElement('button');
    dismiss.type = 'button';
    dismiss.className = 'whats-new-dismiss';
    dismiss.textContent = '×';
    dismiss.setAttribute('aria-label', 'Hide for this session');
    dismiss.setAttribute('title', 'Hide for this session');
    dismiss.addEventListener('click', function () {
      try { sessionStorage.setItem(STRIP_DISMISS_KEY, '1'); } catch (e) {}
      strip.remove();
      capture('whats_new_dismiss', { sections: sections });
    });
    strip.appendChild(dismiss);

    parent.insertBefore(strip, anchor);
    capture('whats_new_view', { sections: sections });
    return sections;
  }

  // The feed page reuses this fetch + read-state helpers for its Editor's
  // Desk inserts instead of requesting /api/updates a second time.
  var state = {
    promise: null,
    data: null,
    stripSections: [],
    unread: function (section) {
      if (!state.data) return false;
      var sig = signalOf(state.data, section);
      return !!sig && isUnread(section, sig);
    },
    fresh: function (section) {
      return !!state.data && isFresh(section, state.data);
    }
  };
  window.llmDigestUpdates = state;

  function run() {
    state.promise = fetch('/api/updates', { headers: { accept: 'application/json' } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; });
    state.promise
      .then(function (u) {
        state.data = u;
        if (!u) return;
        injectStyle();
        var cur = currentSection();
        var stripEligible = [];
        Object.keys(ROUTE).forEach(function (route) {
          var section = ROUTE[route];
          if (section === cur) return;
          var signal = signalOf(u, section);
          if (!signal || !isUnread(section, signal) || !isFresh(section, u)) return;
          decorate(section);
          // Strip chips only for sections this reader has visited before —
          // a first-time or section-uninterested reader is introduced through
          // the Editor's Desk pills and in-feed cards, never a nag strip.
          if (getItem(SEEN[section])) stripEligible.push(section);
        });
        if (cur) {
          var sig = signalOf(u, cur);
          if (sig) setItem(SEEN[cur], sig);
        }
        if (isFeedPage() && stripEligible.length && !isStripDismissed()) {
          state.stripSections = renderStrip(u, stripEligible);
        }
      })
      .catch(function () {});
  }

  // Per-topic read log for the /map knowledge universe: opening a know-how
  // page (/topic/<slug>, any locale) records slug → epoch ms. The orbit view
  // reads this to dim planets/lights the reader has already absorbed. Local
  // only — never sent anywhere.
  var TOPIC_READS_KEY = 'ai_feed_topic_reads_v1';
  function recordTopicRead() {
    var m = location.pathname.match(/^(?:\/[a-z]{2})?\/topic\/([a-z0-9][a-z0-9-]{0,80})\/?$/);
    if (!m) return;
    try {
      var reads = {};
      try { reads = JSON.parse(getItem(TOPIC_READS_KEY) || '{}') || {}; } catch (e) {}
      reads[m[1]] = Date.now();
      var slugs = Object.keys(reads);
      if (slugs.length > 500) {
        slugs.sort(function (a, b) { return reads[a] - reads[b]; })
          .slice(0, slugs.length - 500)
          .forEach(function (s) { delete reads[s]; });
      }
      setItem(TOPIC_READS_KEY, JSON.stringify(reads));
    } catch (e) {}
  }
  recordTopicRead();

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();
