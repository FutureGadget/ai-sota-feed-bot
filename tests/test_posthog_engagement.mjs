// web/posthog-client.js labels visits so analytics can separate readers from
// the sitemap crawler (decision-log 2026-11-14): every event carries
// `profile_state`, and `engaged_visit` fires once on the first trusted input
// or after 10s of visible time. A crawler page that opens in a new profile and
// closes at once is `fresh` with no `engaged_visit`.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../web/posthog-client.js', import.meta.url), 'utf8');
const READER_ID = 'anon_0b3c9a3e-5d1f-4c1e-9a55-2f1f0c7d9e11';

function makeTarget() {
  const listeners = {};
  return {
    addEventListener(type, fn) {
      (listeners[type] ||= []).push(fn);
    },
    removeEventListener(type, fn) {
      listeners[type] = (listeners[type] || []).filter((f) => f !== fn);
    },
    dispatch(type, event = {}) {
      for (const fn of [...(listeners[type] || [])]) fn({ type, isTrusted: true, ...event });
    },
    count(type) {
      return (listeners[type] || []).length;
    },
  };
}

async function load(href = 'https://www.llm-digest.com/daily/2026-11-13', { stored = {}, hidden = false } = {}) {
  let now = 1_000_000;
  let nextId = 1;
  const timers = new Map();
  const captured = [];
  const registered = [];
  const win = makeTarget();
  const doc = makeTarget();
  doc.visibilityState = hidden ? 'hidden' : 'visible';

  Object.assign(win, {
    location: new URL(href),
    history: { state: null, replaceState() {} },
    crypto: { randomUUID: () => '11111111-2222-4333-8444-555555555555' },
    document: doc,
    innerHeight: 800,
    requestAnimationFrame() {},
    setTimeout(fn, ms) {
      const id = nextId++;
      timers.set(id, { fn, at: now + ms });
      return id;
    },
    clearTimeout(id) {
      timers.delete(id);
    },
    // A loaded SDK: `__SV` makes the snippet installer a no-op and init()
    // runs the client's `loaded` callback straight away.
    posthog: {
      __SV: 1,
      init: (_key, config) => config.loaded(win.posthog),
      register: (props) => registered.push(props),
      identify() {},
      capture: (event, props) => captured.push([event, props]),
    },
  });

  const context = vm.createContext({
    URL,
    window: win,
    document: doc,
    localStorage: {
      getItem: (k) => (Object.hasOwn(stored, k) ? stored[k] : null),
      setItem: (k, v) => {
        stored[k] = String(v);
      },
    },
    fetch: async () => ({
      ok: true,
      json: async () => ({ posthog: { enabled: true, project_api_key: 'phc_test' } }),
    }),
    console: { debug() {} },
    Date: { now: () => now },
  });
  vm.runInContext(source, context);
  await new Promise((resolve) => setImmediate(resolve));

  // Objects built inside the vm context have its own Object prototype.
  const plain = (value) => JSON.parse(JSON.stringify(value));
  return {
    api: win.aiFeedPostHog,
    win,
    get registered() {
      return plain(registered);
    },
    engaged: () => plain(captured.filter(([event]) => event === 'engaged_visit').map(([, props]) => props)),
    advance(ms) {
      now += ms;
      for (const [id, t] of [...timers]) {
        if (t.at <= now) {
          timers.delete(id);
          t.fn();
        }
      }
    },
    setVisibility(state) {
      doc.visibilityState = state;
      doc.dispatch('visibilitychange');
    },
  };
}

test('registers profile_state before the first pageview', async () => {
  const fresh = await load();
  assert.deepEqual(fresh.registered, [{ profile_state: 'fresh' }]);

  const returning = await load(undefined, { stored: { ai_feed_anon_user_id: 'anon_existing' } });
  assert.deepEqual(returning.registered, [{ profile_state: 'returning' }]);
});

test('an email rid link counts as a returning reader in a new browser', async () => {
  const h = await load(`https://www.llm-digest.com/daily/2026-11-13?utm_source=email&rid=${READER_ID}`);
  assert.equal(h.api.getProfileState(), 'returning');
  assert.deepEqual(h.registered, [{ profile_state: 'returning' }]);
});

test('a page left inside the dwell window without input is never engaged', async () => {
  const h = await load();
  h.advance(9_999);
  assert.deepEqual(h.engaged(), []);
});

test('10 seconds of visible time is an engaged visit, reported once', async () => {
  const h = await load();
  h.advance(10_000);
  h.advance(60_000);
  h.win.dispatch('pointerdown');
  assert.deepEqual(h.engaged(), [{ path: '/daily/2026-11-13', trigger: 'dwell', ms_since_load: 10_000 }]);
});

test('a trusted input engages at once and stops the listeners', async () => {
  const h = await load();
  h.advance(1_500);
  h.win.dispatch('keydown');
  h.advance(30_000);
  assert.deepEqual(h.engaged(), [{ path: '/daily/2026-11-13', trigger: 'keydown', ms_since_load: 1_500 }]);
  for (const type of ['pointerdown', 'keydown', 'wheel', 'touchstart']) assert.equal(h.win.count(type), 0);
});

test('synthetic (untrusted) input does not count as engagement', async () => {
  const h = await load();
  h.win.dispatch('pointerdown', { isTrusted: false });
  h.advance(5_000);
  assert.deepEqual(h.engaged(), []);
});

test('only visible time counts toward the dwell', async () => {
  const h = await load(undefined, { hidden: true });
  h.advance(60_000);
  assert.deepEqual(h.engaged(), []);

  h.setVisibility('visible');
  h.advance(6_000);
  h.setVisibility('hidden');
  h.advance(60_000);
  assert.deepEqual(h.engaged(), []);

  h.setVisibility('visible');
  h.advance(3_999);
  assert.deepEqual(h.engaged(), []);
  h.advance(1);
  assert.equal(h.engaged().length, 1);
  assert.equal(h.engaged()[0].trigger, 'dwell');
});

test('starting tracking again does not add a second report', async () => {
  const h = await load();
  h.api.startEngagementTracking();
  h.advance(10_000);
  assert.equal(h.engaged().length, 1);
});
