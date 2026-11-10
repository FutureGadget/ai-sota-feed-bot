// Watchlist: readers pick the tools, model families and topics they run, and
// the site shows what changed for those since they last looked.
// Contract: docs/product-specs/watchlist.md.
//
// - /watch-data.json (pipeline/watch.py) lists the entities, their matching
//   rules and their recent stories.
// - Any element with `data-watch-title` (and optional `data-watch-source`,
//   `data-watch-context`) is filled with Watch chips for the entities that
//   title is news about. Feed cards and story pages both use this.
// - `#watchHome` on the feed becomes the watchlist module.
// - State lives in this browser (localStorage). Adding an email upgrades it to
//   alerts through POST /api/subscribe { action: "watch" } (lib/follow.js).
//
// The matching rules mirror pipeline/watch.py; tests/fixtures/
// watch_match_cases.json pins both. Defensive throughout: any failure leaves
// the page as it was.
(() => {
  const WATCH_KEY = "ai_feed_watchlist_v1";
  const EMAIL_KEY = "ai_feed_watch_email_v1";
  const INTRO_KEY = "ai_feed_watch_intro_dismissed_v1";
  const SLUG_RE = /^[a-z0-9][a-z0-9-]{0,99}$/;
  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const MAX_WATCHES = 25; // lib/follow.js MAX_FOLLOWS
  const NEW_WINDOW_MS = 7 * 86400000;
  const ROWS_PER_ENTITY = 2;
  const MAX_ROWS = 6;
  const KIND_LABELS = { tool: "Tools", model: "Models", topic: "Topics" };

  // ---------------------------------------------------------------- matching
  const normalize = (text) => {
    const s = String(text || "").toLowerCase().replace(/[^a-z0-9.+]+/g, " ").replace(/\.+(?= |$)/g, "");
    return ` ${s.split(" ").filter(Boolean).join(" ")} `;
  };

  const compileTerm = (term) => {
    const raw = String(term || "").trim();
    const prefix = raw.endsWith("*");
    const body = normalize(raw.replace(/\*+$/, "")).trim();
    return body ? { body, prefix } : null;
  };

  const matchEntities = (title, source, entities) => {
    const norm = normalize(title);
    const src = String(source || "").trim();
    const out = [];
    for (const ent of entities || []) {
      if (src && (ent.sources || []).includes(src)) {
        out.push(ent.slug);
        continue;
      }
      let text = norm;
      for (const phrase of ent.not || []) text = text.split(normalize(phrase)).join(" ");
      const hit = (ent.terms || []).some((term) => {
        const t = compileTerm(term);
        return !!t && text.includes(t.prefix ? ` ${t.body}` : ` ${t.body} `);
      });
      if (hit) out.push(ent.slug);
    }
    return out;
  };

  // Stories for one watched entity that arrived after the reader last marked
  // it seen. Capped at a week so a long absence does not bury the feed.
  const unseenItems = (entity, seen, now = Date.now()) => {
    const floor = Math.max(Date.parse(seen || "") || 0, now - NEW_WINDOW_MS);
    return (entity?.items || []).filter((item) => (Date.parse(item.first_seen || "") || 0) > floor);
  };

  const api = { normalize, matchEntities, unseenItems };
  globalThis.llmDigestWatch = api;
  if (typeof document === "undefined") return;

  // ------------------------------------------------------------------- state
  const readJson = (key) => {
    try {
      const value = JSON.parse(localStorage.getItem(key) || "{}");
      return value && typeof value === "object" ? value : {};
    } catch {
      return {};
    }
  };
  const writeJson = (key, value) => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {}
  };
  const capture = (event, props) => {
    try {
      window.aiFeedPostHog?.capture?.(event, props);
    } catch {}
  };
  const esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  let data = null; // { entities: [...] }
  let bySlug = new Map();
  let emailEnabled = false;
  let editorOpen = false;
  let emailFormOpen = false;
  let homeViewCaptured = false;
  let formSeq = 0;

  const watches = () => {
    const raw = readJson(WATCH_KEY);
    const out = {};
    for (const [slug, value] of Object.entries(raw)) {
      if (SLUG_RE.test(slug) && bySlug.has(slug)) out[slug] = value && typeof value === "object" ? value : {};
    }
    return out;
  };
  const watchedSlugs = () => Object.keys(watches());
  const emailedSlugs = () => {
    const slugs = readJson(EMAIL_KEY).slugs;
    return Array.isArray(slugs) ? slugs.filter((s) => SLUG_RE.test(s)) : [];
  };
  const uncoveredSlugs = () => {
    const covered = new Set(emailedSlugs());
    return watchedSlugs().filter((slug) => !covered.has(slug));
  };

  const toggle = (slug, surface) => {
    if (!bySlug.has(slug)) return false;
    const state = readJson(WATCH_KEY);
    let on;
    if (state[slug]) {
      delete state[slug];
      on = false;
    } else {
      if (Object.keys(state).length >= MAX_WATCHES) return false;
      const now = new Date().toISOString();
      state[slug] = { added_at: now, seen: now };
      on = true;
    }
    writeJson(WATCH_KEY, state);
    capture("watch_toggle", { slug, action: on ? "watch" : "unwatch", surface, total: Object.keys(state).length });
    return on;
  };

  const markAllSeen = () => {
    const state = readJson(WATCH_KEY);
    const now = new Date().toISOString();
    for (const slug of Object.keys(state)) state[slug] = { ...(state[slug] || {}), seen: now };
    writeJson(WATCH_KEY, state);
  };

  // --------------------------------------------------------------- rendering
  const chipHtml = (slug, surface) => {
    const ent = bySlug.get(slug);
    if (!ent) return "";
    const on = !!watches()[slug];
    return `<button type="button" class="watch-chip" data-watch-slug="${esc(slug)}" data-watch-surface="${esc(surface)}" aria-pressed="${on}">${on ? "✓" : "+"} ${esc(ent.label)}</button>`;
  };

  const relTime = (iso) => {
    const t = Date.parse(iso || "");
    if (!Number.isFinite(t)) return "";
    const hours = Math.floor((Date.now() - t) / 3600000);
    if (hours < 1) return "just now";
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  const readerId = () => {
    try {
      return window.aiFeedPostHog?.getAnonUserId?.() || "";
    } catch {
      return "";
    }
  };

  const setMessage = (form, text, state) => {
    const message = form.querySelector(".subscribe-inline-msg");
    if (!message) return;
    message.textContent = text;
    message.dataset.state = state || "";
    message.hidden = !text;
  };

  const submitEmail = async (form, surface) => {
    const input = form.elements.email;
    const button = form.querySelector("button[type=submit]");
    const email = String(input.value || "").trim();
    const honeypot = String(form.elements.website?.value || "").trim();
    const slugs = watchedSlugs();
    if (!EMAIL_RE.test(email)) {
      setMessage(form, "Please enter a valid email address.", "err");
      input.focus();
      return;
    }
    button.disabled = true;
    setMessage(form, "Saving…", "");
    try {
      const response = await fetch("/api/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "watch", email, slugs, hp: honeypot, reader_id: readerId() }),
      });
      if (response.ok) {
        if (!honeypot) {
          const merged = [...new Set([...emailedSlugs(), ...slugs])];
          writeJson(EMAIL_KEY, { slugs: merged, at: new Date().toISOString() });
          capture("watch_email_success", { surface, count: slugs.length });
        }
        input.disabled = true;
        button.remove();
        form.querySelectorAll(".subscribe-inline-note").forEach((note) => note.remove());
        setMessage(form, "✓ We’ll email you on days something you watch changes.", "ok");
        emailFormOpen = false;
        return;
      }
      setMessage(
        form,
        response.status === 400
          ? "Please enter a valid email address."
          : "Email alerts are temporarily unavailable. Please try again shortly.",
        "err",
      );
    } catch {
      setMessage(form, "Network error. Check your connection and try again.", "err");
    }
    button.disabled = false;
  };

  const buildEmailForm = (surface) => {
    formSeq += 1;
    const id = `watchEmail${formSeq}`;
    const form = document.createElement("form");
    form.className = "subscribe-inline watch-email-form";
    form.noValidate = true;
    form.innerHTML = `
      <p class="subscribe-inline-kicker">Email alert · only what you watch</p>
      <label class="subscribe-inline-label" for="${id}">Email address for watchlist alerts</label>
      <div class="subscribe-inline-row">
        <input id="${id}" type="email" name="email" required placeholder="you@example.com" autocomplete="email" inputmode="email" />
        <input type="text" name="website" class="subscribe-inline-hp" tabindex="-1" autocomplete="off" aria-hidden="true" />
        <button type="submit">Email me</button>
      </div>
      <p class="subscribe-inline-note">At most one email a day, only when something you watch changes · stop from any alert</p>
      <p class="subscribe-inline-msg" role="status" aria-live="polite" hidden></p>`;
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      submitEmail(form, surface);
    });
    capture("watch_email_view", { surface });
    return form;
  };

  // Email slot: an offer, a form, or a status line, depending on what this
  // browser has already sent. Never rebuilt while the reader is typing.
  const paintEmailSlot = (slot, surface, forceOpen = false) => {
    if (!slot || slot.querySelector("form")) return;
    const watched = watchedSlugs();
    if (!emailEnabled || !watched.length) {
      slot.hidden = true;
      slot.replaceChildren();
      return;
    }
    slot.hidden = false;
    const uncovered = uncoveredSlugs();
    const emailed = emailedSlugs().length > 0;
    if (!uncovered.length) {
      slot.innerHTML = `<p class="watch-email-status">✓ Email alerts are on for your watchlist.</p>`;
      return;
    }
    if (forceOpen || emailFormOpen) {
      slot.replaceChildren(buildEmailForm(surface));
      return;
    }
    slot.innerHTML = emailed
      ? `<p class="watch-email-status">Email alerts cover ${watched.length - uncovered.length} of ${watched.length}. <button type="button" class="watch-link" data-watch-email-open>Update</button></p>`
      : `<button type="button" class="watch-link" data-watch-email-open>Email me when these change</button>`;
  };

  const editorHtml = () =>
    ["tool", "model", "topic"]
      .map((kind) => {
        const chips = data.entities.filter((e) => e.kind === kind).map((e) => chipHtml(e.slug, "home_editor")).join("");
        return chips ? `<div class="watch-editor-group"><p class="watch-editor-kind">${KIND_LABELS[kind]}</p><div class="watch-chips">${chips}</div></div>` : "";
      })
      .join("");

  // A first-time reader sees the busiest few entities: tools and model
  // families first, because "what do you run" is easier to answer than a topic.
  const introSlugs = () => {
    const top = (kind, n) =>
      data.entities.filter((e) => e.kind === kind && e.count > 0).sort((a, b) => b.count - a.count).slice(0, n).map((e) => e.slug);
    return [...top("tool", 4), ...top("model", 3)];
  };

  const homeRows = () => {
    const state = watches();
    const rows = [];
    let total = 0;
    for (const slug of Object.keys(state)) {
      const ent = bySlug.get(slug);
      const fresh = unseenItems(ent, state[slug].seen);
      total += fresh.length;
      fresh.slice(0, ROWS_PER_ENTITY).forEach((item, i) => {
        const extra = i === ROWS_PER_ENTITY - 1 ? fresh.length - ROWS_PER_ENTITY : 0;
        rows.push({ ent, item, extra });
      });
    }
    rows.sort((a, b) => String(b.item.first_seen).localeCompare(String(a.item.first_seen)));
    return { rows: rows.slice(0, MAX_ROWS), total };
  };

  const renderHome = () => {
    const root = document.getElementById("watchHome");
    if (!root || !data) return;
    const slugs = watchedSlugs();
    const introDismissed = (() => {
      try {
        return localStorage.getItem(INTRO_KEY) === "1";
      } catch {
        return false;
      }
    })();

    if (!slugs.length && introDismissed && !editorOpen) {
      root.hidden = true;
      root.replaceChildren();
      return;
    }
    root.hidden = false;
    const keepForm = root.querySelector(".watch-email-slot form");

    let html;
    let viewState;
    let newCount = 0;
    if (!slugs.length) {
      viewState = "intro";
      html = `
        <div class="watch-home-head">
          <h2 class="watch-home-title">Watch what you run</h2>
          <button type="button" class="watch-dismiss" data-watch-intro-dismiss aria-label="Hide the watchlist prompt" title="Hide">×</button>
        </div>
        <p class="watch-home-copy">Pick the tools and models you use. This page will show what changed for them since your last visit.</p>
        ${editorOpen ? "" : `<div class="watch-chips watch-intro-chips">${introSlugs().map((s) => chipHtml(s, "home_intro")).join("")}<button type="button" class="watch-link" data-watch-edit>All ${data.entities.length} →</button></div>`}`;
    } else {
      const { rows, total } = homeRows();
      newCount = total;
      viewState = total ? "new" : "quiet";
      const list = rows
        .map(({ ent, item, extra }) => `
          <li class="watch-row">
            <span class="watch-row-label">${esc(ent.label)}</span>
            <a href="/story/${esc(item.sid)}" data-watch-item="${esc(ent.slug)}">${esc(item.title)}</a>
            <span class="watch-row-when">${esc(relTime(item.first_seen))}${extra > 0 ? ` · +${extra} more` : ""}</span>
          </li>`)
        .join("");
      html = `
        <div class="watch-home-head">
          <h2 class="watch-home-title">Your watchlist</h2>
          <span class="watch-home-count">${total ? `${total} new` : `Nothing new in ${slugs.length} watched`}</span>
          <span class="watch-home-actions">
            ${total ? `<button type="button" class="watch-link" data-watch-seen>Mark seen</button>` : ""}
            <button type="button" class="watch-link" data-watch-edit aria-expanded="${editorOpen}">${editorOpen ? "Done" : "Edit"}</button>
          </span>
        </div>
        ${list ? `<ul class="watch-rows">${list}</ul>` : ""}`;
    }
    html += `${editorOpen ? `<div class="watch-editor">${editorHtml()}${slugs.length ? "" : `<p class="watch-email-status"><button type="button" class="watch-link" data-watch-edit>Show fewer</button></p>`}</div>` : ""}<div class="watch-email-slot" hidden></div>`;
    root.innerHTML = html;
    const slot = root.querySelector(".watch-email-slot");
    if (keepForm) {
      slot.hidden = false;
      slot.replaceChildren(keepForm);
    } else {
      paintEmailSlot(slot, "home");
    }
    if (!homeViewCaptured) {
      homeViewCaptured = true;
      capture("watch_home_view", { state: viewState, watched: slugs.length, new_count: newCount });
    }
  };

  const hydrate = (root = document) => {
    if (!data) return;
    root.querySelectorAll?.("[data-watch-title]:not([data-watch-done])").forEach((el) => {
      el.setAttribute("data-watch-done", "");
      const slugs = matchEntities(el.dataset.watchTitle, el.dataset.watchSource, data.entities);
      if (!slugs.length) return;
      const surface = el.dataset.watchContext === "story" ? "story" : "card";
      const chips = slugs.map((slug) => chipHtml(slug, surface)).join("");
      el.innerHTML = surface === "story"
        ? `<p class="tldr-label">Watch</p>
           <p class="watch-box-copy">Watch a topic to see what changed for it next time you visit.</p>
           <div class="watch-chips">${chips}</div>
           <p class="watch-box-hint" hidden>Watching in this browser. New coverage shows at the top of the <a href="/">live feed</a>.</p>
           <div class="watch-email-slot" hidden></div>`
        : `<span class="watch-chips-label">Watch</span><div class="watch-chips">${chips}</div>`;
      el.hidden = false;
      if (surface === "story") paintStoryBox(el);
    });
  };

  const paintStoryBox = (box, justWatched = false) => {
    const any = [...box.querySelectorAll("[data-watch-slug]")].some((chip) => chip.getAttribute("aria-pressed") === "true");
    const hint = box.querySelector(".watch-box-hint");
    if (hint) hint.hidden = !any;
    paintEmailSlot(box.querySelector(".watch-email-slot"), "story", justWatched);
  };

  const repaintChips = () => {
    const state = watches();
    document.querySelectorAll("[data-watch-slug]").forEach((chip) => {
      const ent = bySlug.get(chip.dataset.watchSlug);
      if (!ent) return;
      const on = !!state[ent.slug];
      chip.setAttribute("aria-pressed", String(on));
      chip.textContent = `${on ? "✓" : "+"} ${ent.label}`;
    });
  };

  const onClick = (event) => {
    const target = event.target instanceof Element ? event.target : null;
    if (!target) return;
    const chip = target.closest("button[data-watch-slug]");
    if (chip) {
      const on = toggle(chip.dataset.watchSlug, chip.dataset.watchSurface || "");
      repaintChips();
      renderHome();
      const box = chip.closest('[data-watch-context="story"]');
      if (box) paintStoryBox(box, on);
      return;
    }
    if (target.closest("[data-watch-edit]")) {
      editorOpen = !editorOpen;
      renderHome();
      return;
    }
    if (target.closest("[data-watch-seen]")) {
      markAllSeen();
      capture("watch_mark_seen", {});
      renderHome();
      return;
    }
    if (target.closest("[data-watch-intro-dismiss]")) {
      try {
        localStorage.setItem(INTRO_KEY, "1");
      } catch {}
      editorOpen = false;
      capture("watch_intro_dismiss", {});
      renderHome();
      return;
    }
    const open = target.closest("[data-watch-email-open]");
    if (open) {
      const slot = open.closest(".watch-email-slot");
      const surface = slot?.closest('[data-watch-context="story"]') ? "story" : "home";
      if (surface === "home") emailFormOpen = true;
      slot.replaceChildren();
      paintEmailSlot(slot, surface, true);
      slot.querySelector("input[type=email]")?.focus();
      return;
    }
    const item = target.closest("a[data-watch-item]");
    if (item) capture("watch_item_click", { slug: item.dataset.watchItem });
  };

  const loadEmailEnabled = async () => {
    try {
      const response = await fetch("/api/client-config", { headers: { accept: "application/json" } });
      const config = response.ok ? await response.json() : null;
      return !!config?.digest?.email_subscribe_enabled && !String(config?.digest?.email_signup_url || "").trim();
    } catch {
      return false;
    }
  };

  const start = async () => {
    try {
      const response = await fetch("/watch-data.json", { headers: { accept: "application/json" } });
      if (!response.ok) return;
      const payload = await response.json();
      if (!Array.isArray(payload?.entities)) return;
      data = { entities: payload.entities.filter((e) => SLUG_RE.test(String(e?.slug || "")) && e.label) };
    } catch {
      return;
    }
    bySlug = new Map(data.entities.map((e) => [e.slug, e]));
    document.addEventListener("click", onClick);
    hydrate();
    renderHome();
    // The feed re-renders its cards on every filter change.
    if ("MutationObserver" in window && document.body) {
      new MutationObserver(() => {
        if (document.querySelector("[data-watch-title]:not([data-watch-done])")) hydrate();
      }).observe(document.body, { childList: true, subtree: true });
    }
    emailEnabled = await loadEmailEnabled();
    if (emailEnabled) {
      renderHome();
      document.querySelectorAll('[data-watch-context="story"][data-watch-done]').forEach((box) => paintStoryBox(box));
    }
  };

  Object.assign(api, { hydrate, renderHome });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
