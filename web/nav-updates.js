/* Editorial discovery: published items, stable content versions, browser-local
 * seen state. The API derives the catalog from every producer's published
 * outputs; see docs/product-specs/nav-update-indicators.md. */
(function () {
  'use strict';
  var KEY = 'ai_feed_editorial_state_v2';
  var DISMISS = 'ai_feed_whats_new_dismissed_v1';
  var ROUTE = { '/daily': 'daily', '/weekly': 'weekly', '/storylines': 'storylines',
    '/playbook': 'playbook', '/map': 'map', '/foundations': 'foundations' };
  var LABELS = { daily: 'Daily recap', weekly: 'Weekly recap', storylines: 'Storylines',
    playbook: 'Playbook', map: 'Agent Know-How', foundations: 'Foundations' };
  var state = { data: null, promise: null, stripSections: [], renderFeed: renderFeed,
    unread: function (section) { return items().some(function (i) { return i.section === section && fresh(i) && status(i) !== 'seen'; }); },
    fresh: function (section) { return items().some(function (i) { return i.section === section && fresh(i); }); } };
  window.llmDigestUpdates = state;
  var memory = null;
  var reader = null;
  var opened = new Set();
  var readyPaths = new Set();
  var sectionPanel = null;
  var viewed = new Set();
  function items() { return state.data && Array.isArray(state.data.items) ? state.data.items : []; }
  function get(store, key) { try { return window[store].getItem(key); } catch (e) { return null; } }
  function set(store, key, value) { try { window[store].setItem(key, value); } catch (e) {} }
  function persist() { set('localStorage', KEY, JSON.stringify(memory)); }
  function loadMemory() {
    try { memory = JSON.parse(get('localStorage', KEY)); } catch (e) {}
    // A quiet baseline preserves discovery without calling the archive new.
    memory = reader.initializeState(memory, items());
    persist();
  }
  function status(item) { return reader.itemStatus(memory, item); }
  function fresh(item) { return reader.isFresh(item, state.data.now); }
  function capture(event, props) {
    try { (window.aiFeedPostHog || window.posthog).capture(event, props); } catch (e) {}
  }
  function node(tag, cls, value) {
    var el = document.createElement(tag);
    if (cls) el.className = cls;
    if (value) el.textContent = value;
    return el;
  }
  function validHref(href) {
    return typeof href === 'string' && /^\/(daily\/\d{4}-\d{2}-\d{2}|weekly\/\d{4}-W\d{2}|playbook\/(?:\d{4}-\d{2}-\d{2}|lab\/[a-z0-9-]+)|storyline\/[a-z0-9-]+|topic\/[a-z0-9-]+|foundations\/[a-z0-9-]+)$/.test(href);
  }
  function dateLabel(item) {
    var date = new Date(item.updated_at);
    if (item.date_precision === 'day') return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
    var hours = Math.floor((Date.parse(state.data.now) - date.getTime()) / 3600000);
    if (hours >= 0 && hours < 1) return 'less than 1h ago';
    if (hours >= 1 && hours < 24) return hours + 'h ago';
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  }
  function row(item, placement) {
    var li = node('li', 'editorial-item');
    var meta = node('div', 'editorial-meta');
    meta.appendChild(node('span', '', item.section_label + (item.kind === 'lab' ? ' · Skill Lab' : '')));
    var itemStatus = status(item);
    if (itemStatus === 'new' || itemStatus === 'updated') meta.appendChild(node('span', 'editorial-badge', itemStatus === 'new' ? 'New' : 'Updated'));
    if (itemStatus === 'seen') meta.appendChild(node('span', '', 'Opened'));
    var time = node('time', '', (item.kind === 'edition' || item.kind === 'lab' ? 'Published ' : 'Updated ') + dateLabel(item));
    time.dateTime = item.updated_at;
    // Day-only source dates never acquire fabricated hour-level precision.
    time.title = item.updated_at;
    meta.appendChild(time);
    var link = node('a', 'editorial-title', item.title);
    link.href = item.href;
    link.addEventListener('click', function () { capture('editorial_update_click', { id: item.id, section: item.section, placement: placement, status: itemStatus }); });
    li.append(meta, link);
    if (item.summary) li.appendChild(node('p', 'editorial-summary', item.summary));
    return li;
  }
  function list(selected, placement) {
    var ul = node('ul', 'editorial-list');
    selected.forEach(function (i) { ul.appendChild(row(i, placement)); });
    return ul;
  }
  function viewAll(section) {
    var a = node('a', 'editorial-all', 'View all updates →');
    a.href = '/updates' + (section ? '?section=' + encodeURIComponent(section) : '');
    return a;
  }
  function panel(selected, title, placement) {
    var el = node('section', 'editorial-panel');
    el.setAttribute('aria-label', title);
    el.appendChild(node('h2', 'editorial-heading', title));
    el.appendChild(list(selected, placement));
    el.appendChild(viewAll());
    return el;
  }
  function renderFeed() {
    var anchor = document.getElementById('freshUpdates');
    if (!anchor || !memory) return;
    var combined = document.querySelector('[data-editorial-catchup]');
    var target = combined || anchor;
    var selected = items().filter(function (i) { return fresh(i) && status(i) !== 'seen'; }).slice(0, 3);
    state.stripSections = [];
    // Deterministic composition: if catch-up exists, editorial rows belong
    // inside it, regardless of which API resolved first.
    anchor.replaceChildren();
    if (combined) combined.replaceChildren();
    if (!selected.length || get('sessionStorage', DISMISS) === '1') return;
    var el = panel(selected, 'Latest from the Editor’s Desk', 'feed');
    var dismiss = node('button', 'editorial-dismiss', 'Hide');
    dismiss.type = 'button';
    dismiss.setAttribute('aria-label', 'Hide editorial updates for this session');
    dismiss.addEventListener('click', function () {
      set('sessionStorage', DISMISS, '1');
      capture('editorial_updates_dismiss', { placement: 'feed' });
      renderFeed();
    });
    el.prepend(dismiss);
    target.appendChild(el);
    state.stripSections = Array.from(new Set(selected.map(function (i) { return i.section; })));
    var signature = selected.map(function (i) { return i.id + ':' + i.version; }).join('|');
    if (!viewed.has(signature)) {
      viewed.add(signature);
      capture('editorial_updates_view', { placement: 'feed', ids: selected.map(function (i) { return i.id; }) });
    }
  }
  function renderDesk() {
    var nav = document.querySelector('.site-nav-fallback');
    if (!nav) return;
    var old = document.getElementById('editorialDeskLatest');
    if (old) old.remove();
    var el = panel(items().slice(0, 3), 'Latest updates', 'desk');
    el.id = 'editorialDeskLatest';
    if (!items().length) el.hidden = true;
    nav.before(el);
    document.querySelectorAll('.site-nav-fallback a[href]').forEach(function (a) {
      a.querySelectorAll('.nav-update-dot, .nav-update-sr').forEach(function (n) { n.remove(); });
      var section = ROUTE[a.getAttribute('href')];
      var count = items().filter(function (i) { return i.section === section && fresh(i) && ['new', 'updated'].includes(status(i)); }).length;
      if (!count) return;
      var badge = node('span', 'nav-update-dot', String(count));
      badge.setAttribute('aria-hidden', 'true');
      a.appendChild(badge);
      a.appendChild(node('span', 'nav-update-sr', ' (' + count + ' new or updated items)'));
    });
  }
  function renderCollection(host, section, limit, placement) {
    var filter = host.querySelector('[data-editorial-filter]').value;
    var sectionSelect = host.querySelector('[data-editorial-section]');
    if (sectionSelect) section = sectionSelect.value;
    var selected = items().filter(function (i) { return (!section || i.section === section) && (filter !== 'unread' || status(i) !== 'seen'); });
    var result = host.querySelector('[data-editorial-results]');
    result.replaceChildren(list(selected.slice(0, limit), placement));
    if (!selected.length) result.appendChild(node('p', 'editorial-empty', filter === 'unread' ? 'You’re caught up here. Browse Latest to revisit an article.' : 'No published updates yet.'));
    host.querySelector('[data-editorial-count]').textContent = selected.length + (filter === 'unread' ? ' unopened items' : ' updates');
  }
  function collection(host, section, limit, placement) {
    var controls = node('div', 'editorial-controls');
    var label = node('label', '', 'Show ');
    var select = node('select');
    select.dataset.editorialFilter = '';
    [['latest', 'Latest'], ['unread', 'Unread']].forEach(function (v) { var o = node('option', '', v[1]); o.value = v[0]; select.appendChild(o); });
    label.appendChild(select); controls.appendChild(label);
    if (!section) {
      var sectionLabel = node('label', '', 'Section ');
      var sections = node('select'); sections.dataset.editorialSection = '';
      var all = node('option', '', 'All sections'); all.value = ''; sections.appendChild(all);
      Object.keys(LABELS).forEach(function (key) { var o = node('option', '', LABELS[key]); o.value = key; sections.appendChild(o); });
      var querySection = new URLSearchParams(location.search).get('section');
      sections.value = LABELS[querySection] ? querySection : '';
      sectionLabel.appendChild(sections); controls.appendChild(sectionLabel);
    }
    var count = node('p', 'editorial-meta'); count.dataset.editorialCount = ''; count.setAttribute('role', 'status');
    var result = node('div'); result.dataset.editorialResults = '';
    host.append(controls, count, result);
    controls.addEventListener('change', function () { renderCollection(host, section, limit, placement); });
    renderCollection(host, section, limit, placement);
  }
  function renderSections() {
    var path = location.pathname.replace(/\/+$/, '') || '/';
    var section = ROUTE[path];
    if (section && !sectionPanel) {
      var chrome = document.querySelector('.site-chrome');
      if (chrome) {
        sectionPanel = node('details', 'editorial-panel editorial-section');
        sectionPanel.appendChild(node('summary', '', 'Latest in ' + LABELS[section]));
        collection(sectionPanel, section, 3, 'section');
        sectionPanel.appendChild(viewAll(section));
        chrome.after(sectionPanel);
      }
    }
    var archive = document.getElementById('editorialUpdates');
    if (archive && !archive.querySelector('[data-editorial-filter]')) {
      archive.replaceChildren(); collection(archive, '', Infinity, 'updates');
    }
  }
  function markOpened(href) {
    if (!memory) return;
    var item = items().find(function (i) { return i.href === href; });
    if (!item || opened.has(item.id + item.version)) return;
    opened.add(item.id + item.version);
    // Merge another tab's opened items before saving this item.
    try {
      var saved = JSON.parse(get('localStorage', KEY));
      if (saved && saved.schema === 2 && saved.seen && typeof saved.seen === 'object') Object.assign(memory.seen, saved.seen);
    } catch (e) {}
    reader.markItemOpened(memory, items(), href);
    persist();
    capture('editorial_update_open', { id: item.id, section: item.section });
  }
  function currentPage() {
    var path = location.pathname.replace(/\/+$/, '') || '/';
    // Localized content may lag its English source. Do not acknowledge an
    // English version merely because a translated page was opened.
    if (/^\/[a-z]{2}\//.test(path)) return;
    if (/^\/playbook(?:\/|$)/.test(path)) return; // dynamic shells report successful render
    if (path === '/daily' || path === '/weekly') {
      var type = path.slice(1);
      var link = document.querySelector('a[href^="/api/' + type + '?"]');
      if (!link) return;
      var params = new URL(link.getAttribute('href'), location.origin).searchParams;
      path += '/' + params.get(type === 'daily' ? 'date' : 'week');
    }
    if (validHref(path)) markOpened(path);
  }
  document.addEventListener('editorial:opened', function (event) {
    if (!validHref(event.detail && event.detail.href) || /^\/[a-z]{2}\//.test(location.pathname)) return;
    readyPaths.add(event.detail.href);
    if (memory) { markOpened(event.detail.href); renderDesk();
      if (sectionPanel) renderCollection(sectionPanel, ROUTE[location.pathname], 3, 'section'); }
  });
  window.addEventListener('storage', function (event) {
    if (event.key !== KEY || !state.data) return;
    loadMemory(); renderDesk(); renderFeed();
    if (sectionPanel) renderCollection(sectionPanel, ROUTE[location.pathname], 3, 'section');
    var archive = document.getElementById('editorialUpdates');
    if (archive) renderCollection(archive, '', Infinity, 'updates');
  });
  function run() {
    if (!document.querySelector('link[href^="/editorial-updates.css"]')) {
      var style = node('link');
      style.rel = 'stylesheet';
      style.href = '/editorial-updates.css?v=20260910';
      document.head.appendChild(style);
    }
    state.promise = Promise.all([
      import('/editorial-state.js?v=20260910'),
      fetch('/api/updates', { headers: { accept: 'application/json' } }).then(function (r) { return r.ok ? r.json() : null; })
    ]).then(function (result) { reader = result[0]; return result[1]; }).catch(function () { return null; });
    state.promise.then(function (data) {
      if (!data || data.catalog_version !== 1 || !Array.isArray(data.items)) throw new Error('catalog unavailable');
      data.items = data.items.filter(function (i) { return i && LABELS[i.section] && validHref(i.href) && typeof i.id === 'string' && /^[0-9a-f]{24}$/.test(i.version); });
      state.data = data;
      loadMemory(); currentPage(); readyPaths.forEach(markOpened);
      if (!/^\/[a-z]{2}\//.test(location.pathname)) markOpened(document.documentElement.dataset.editorialOpened);
      renderDesk(); renderFeed(); renderSections();
    }).catch(function () {
      var archive = document.getElementById('editorialUpdates');
      if (archive) archive.textContent = 'Updates are temporarily unavailable. Browse the Editor’s Desk sections or reload to try again.';
    });
  }

  // Keep the knowledge-universe's independent topic visit log compatible.
  var topic = location.pathname.match(/^(?:\/[a-z]{2})?\/topic\/([a-z0-9][a-z0-9-]{0,80})\/?$/);
  if (topic) {
    try {
      var reads = JSON.parse(get('localStorage', 'ai_feed_topic_reads_v1') || '{}') || {};
      reads[topic[1]] = Date.now();
      Object.keys(reads).sort(function (a, b) { return reads[b] - reads[a]; }).slice(500).forEach(function (s) { delete reads[s]; });
      set('localStorage', 'ai_feed_topic_reads_v1', JSON.stringify(reads));
    } catch (e) {}
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run);
  else run();
})();
