// web/posthog-client.js sends `recap_link_click` for the links the static
// recap, story and storyline pages tag with `data-track` (autocapture is off,
// so these clicks were invisible before 2026-11-28). The home feed's
// `item-link` stays out: index.html sends it as `click` for auto_tune.py.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../web/posthog-client.js', import.meta.url), 'utf8');

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
  };
}

// A minimal link element: `closest` walks a parent chain by tag and attribute.
function makeLink({ track, href, sectionId = null }) {
  const section = sectionId ? { tag: 'section', attrs: { id: sectionId }, parent: null } : null;
  const link = { tag: 'a', attrs: { 'data-track': track, href }, parent: section };
  const matches = (node, selector) => {
    if (selector === 'a[data-track]') return node.tag === 'a' && 'data-track' in node.attrs;
    if (selector === 'section[id]') return node.tag === 'section' && 'id' in node.attrs;
    return false;
  };
  for (const node of [link, section].filter(Boolean)) {
    node.getAttribute = (name) => (name in node.attrs ? node.attrs[name] : null);
    node.closest = (selector) => {
      for (let n = node; n; n = n.parent) if (matches(n, selector)) return n;
      return null;
    };
  }
  return link;
}

async function load(links) {
  const captured = [];
  const win = makeTarget();
  const doc = makeTarget();
  doc.visibilityState = 'visible';
  doc.querySelectorAll = (selector) => {
    const track = /data-track="([^"]+)"/.exec(selector)?.[1];
    return links.filter((l) => l.attrs['data-track'] === track);
  };
  Object.assign(win, {
    location: new URL('https://www.llm-digest.com/daily/2026-11-20'),
    history: { state: null, replaceState() {} },
    crypto: { randomUUID: () => '11111111-2222-4333-8444-555555555555' },
    document: doc,
    innerHeight: 800,
    requestAnimationFrame() {},
    setTimeout: () => 0,
    clearTimeout() {},
    posthog: {
      __SV: 1,
      init: (_key, config) => config.loaded(win.posthog),
      register() {},
      identify() {},
      capture: (event, props) => captured.push([event, props]),
    },
  });
  const context = vm.createContext({
    URL,
    window: win,
    document: doc,
    localStorage: { getItem: () => null, setItem() {} },
    fetch: async () => ({
      ok: true,
      json: async () => ({ posthog: { enabled: true, project_api_key: 'phc_test' } }),
    }),
    console: { debug() {} },
    Date,
  });
  vm.runInContext(source, context);
  await new Promise((resolve) => setImmediate(resolve));
  return {
    api: win.aiFeedPostHog,
    doc,
    clicks: () =>
      JSON.parse(JSON.stringify(captured.filter(([e]) => e === 'recap_link_click').map(([, p]) => p))),
  };
}

test('a recap article link sends recap_link_click with its place on the page', async () => {
  const first = makeLink({ track: 'daily-link', href: 'https://github.com/a/b', sectionId: 'agents' });
  const second = makeLink({ track: 'daily-link', href: 'https://sandscale.dev', sectionId: 'agents' });
  const h = await load([first, second]);
  h.doc.dispatch('click', { target: second });
  assert.deepEqual(h.clicks(), [
    {
      track: 'daily-link',
      url: 'https://sandscale.dev',
      external: true,
      path: '/daily/2026-11-20',
      section: 'agents',
      position: 2,
    },
  ]);
});

test('an internal story link is reported as not external', async () => {
  const link = makeLink({ track: 'story-link', href: '/story/7c2df92116551afa' });
  const h = await load([link]);
  h.doc.dispatch('click', { target: link });
  assert.equal(h.clicks().length, 1);
  assert.equal(h.clicks()[0].external, false);
  assert.equal(h.clicks()[0].section, null);
});

test('the home feed item-link is left to index.html', async () => {
  const link = makeLink({ track: 'item-link', href: 'https://example.com' });
  const h = await load([link]);
  h.doc.dispatch('click', { target: link });
  assert.deepEqual(h.clicks(), []);
});

test('untrusted clicks and non-middle auxclicks are ignored; middle-click counts', async () => {
  const link = makeLink({ track: 'weekly-link', href: 'https://example.com' });
  const h = await load([link]);
  h.doc.dispatch('click', { target: link, isTrusted: false });
  h.doc.dispatch('auxclick', { target: link, button: 2 });
  assert.deepEqual(h.clicks(), []);
  h.doc.dispatch('auxclick', { target: link, button: 1 });
  assert.equal(h.clicks().length, 1);
});

test('starting link tracking again does not double-report', async () => {
  const link = makeLink({ track: 'daily-link', href: 'https://example.com' });
  const h = await load([link]);
  h.api.startLinkTracking();
  h.doc.dispatch('click', { target: link });
  assert.equal(h.clicks().length, 1);
});
