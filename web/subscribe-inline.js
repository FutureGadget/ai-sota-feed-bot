// Inline email signup at finish points (feed "caught up" marker, story /
// recap / storyline page ends). Progressive enhancement: each
// `a[data-subscribe-inline]` CTA stays a plain link to /subscribe unless
// /api/client-config says in-page signup is enabled, in which case an email
// form replaces it in place, saving the extra page load. Readers this browser
// already subscribed never see the ask. Defensive: any failure keeps the link.
(() => {
  const SUBSCRIBED_KEY = "ai_feed_email_subscribed_v1";
  const NUDGE_DONE_KEY = "ai_feed_subscribe_nudge_done_v1";
  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const CTA_SELECTOR = "a[data-subscribe-inline]:not([data-subscribe-inline-done])";
  const viewed = new Set();
  let configPromise = null;
  let formSeq = 0;

  const capture = (event, props) => {
    try {
      window.aiFeedPostHog?.capture?.(event, props);
    } catch {}
  };

  const isSubscribed = () => {
    try {
      return localStorage.getItem(SUBSCRIBED_KEY) === "1";
    } catch {
      return false;
    }
  };

  const markSubscribed = () => {
    try {
      localStorage.setItem(SUBSCRIBED_KEY, "1");
      localStorage.setItem(NUDGE_DONE_KEY, "1");
    } catch {}
  };

  const readerId = () => {
    try {
      return window.aiFeedPostHog?.getAnonUserId?.() || "";
    } catch {
      return "";
    }
  };

  const inlineEnabled = (config) =>
    !!config?.digest?.email_subscribe_enabled && !String(config?.digest?.email_signup_url || "").trim();

  const loadConfig = () => {
    if (!configPromise) {
      configPromise = fetch("/api/client-config", { headers: { accept: "application/json" } })
        .then((response) => (response.ok ? response.json() : null))
        .catch(() => null);
    }
    return configPromise;
  };

  // The CTA's container: the static-page aside, or the link itself in the feed.
  const ctaContainer = (link) => link.closest(".subscribe-cta") || link;

  const observeView = (form, placement, event = "subscribe_form_view", props = { placement, surface: "inline" }) => {
    const record = () => {
      if (viewed.has(`${event}:${placement}`)) return;
      viewed.add(`${event}:${placement}`);
      capture(event, props);
    };
    if (!("IntersectionObserver" in window)) {
      record();
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      observer.disconnect();
      record();
    }, { threshold: 0.5 });
    observer.observe(form);
  };

  const setMessage = (form, text, state) => {
    const message = form.querySelector(".subscribe-inline-msg");
    if (!message) return;
    message.textContent = text;
    message.dataset.state = state || "";
    message.hidden = !text;
  };

  const submit = async (form, placement) => {
    const input = form.elements.email;
    const button = form.querySelector("button[type=submit]");
    const email = String(input.value || "").trim();
    const honeypot = String(form.elements.website?.value || "").trim();
    if (!EMAIL_RE.test(email)) {
      setMessage(form, "Please enter a valid email address.", "err");
      input.focus();
      return;
    }
    button.disabled = true;
    setMessage(form, "Subscribing…", "");
    try {
      const response = await fetch("/api/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, weekly_only: false, hp: honeypot, reader_id: readerId() }),
      });
      if (response.ok) {
        // A filled honeypot gets the same neutral UI but never counts.
        if (!honeypot) {
          markSubscribed();
          capture("subscribe_success", { cadence: "both", placement, surface: "inline" });
        }
        input.disabled = true;
        button.remove();
        form.querySelector(".subscribe-inline-note")?.remove();
        setMessage(form, "You’re subscribed. The next brief will arrive by email.", "ok");
        return;
      }
      setMessage(
        form,
        response.status === 400
          ? "Please enter a valid email address."
          : "Subscription is temporarily unavailable. Please try again shortly.",
        "err",
      );
    } catch {
      setMessage(form, "Network error. Check your connection and try again.", "err");
    }
    button.disabled = false;
  };

  const buildForm = (placement, kicker = "") => {
    formSeq += 1;
    const id = `subscribeInlineEmail${formSeq}`;
    const form = document.createElement("form");
    form.className = "subscribe-inline";
    form.noValidate = true;
    form.dataset.subscribePlacement = placement;
    form.innerHTML = `
      ${kicker ? `<p class="subscribe-inline-kicker">${kicker}</p>` : ""}
      <label class="subscribe-inline-label" for="${id}">Email address</label>
      <div class="subscribe-inline-row">
        <input id="${id}" type="email" name="email" required placeholder="you@example.com" autocomplete="email" inputmode="email" />
        <input type="text" name="website" class="subscribe-inline-hp" tabindex="-1" autocomplete="off" aria-hidden="true" />
        <button type="submit">Subscribe</button>
      </div>
      <p class="subscribe-inline-note">Daily + weekly · unsubscribe anytime ·
        <a href="/subscribe" data-subscribe-channel="email" data-subscribe-placement="${placement}_options">Weekly only →</a></p>
      <p class="subscribe-inline-msg" role="status" aria-live="polite" hidden></p>`;
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      submit(form, placement);
    });
    return form;
  };

  const enhance = async (root = document) => {
    const links = Array.from(root.querySelectorAll?.(CTA_SELECTOR) || []);
    if (!links.length) return;
    links.forEach((link) => link.setAttribute("data-subscribe-inline-done", ""));
    if (isSubscribed()) {
      links.forEach((link) => {
        ctaContainer(link).hidden = true;
      });
      return;
    }
    if (!inlineEnabled(await loadConfig())) return;
    links.forEach((link) => {
      if (!link.isConnected) return;
      const raw = String(link.dataset.subscribePlacement || "");
      const placement = /^[a-z0-9_-]{1,40}$/.test(raw) ? raw : "inline";
      // Static-page CTAs carry their own heading; the feed's finish line
      // needs a label so the field isn't anonymous.
      const form = buildForm(placement, link.closest(".subscribe-cta") ? "" : "The next brief, by email");
      link.insertAdjacentElement("afterend", form);
      link.hidden = true;
      observeView(form, placement);
    });
  };

  // Storyline follow-by-email (lib/follow.js via /api/subscribe). Once a reader follows a story
  // in this browser, offer to email them when it moves — the Follow click is
  // the moment of intent. Stories already followed by email show a confirmation.
  const FOLLOWS_KEY = "ai_feed_storyline_follows_v1";
  const EMAIL_FOLLOWS_KEY = "ai_feed_storyline_email_follows_v1";
  const SLUG_RE = /^[a-z0-9][a-z0-9-]{0,99}$/;

  const readJson = (key) => {
    try {
      return JSON.parse(localStorage.getItem(key) || "{}") || {};
    } catch {
      return {};
    }
  };

  const markEmailFollow = (slug) => {
    try {
      const follows = readJson(EMAIL_FOLLOWS_KEY);
      follows[slug] = new Date().toISOString();
      localStorage.setItem(EMAIL_FOLLOWS_KEY, JSON.stringify(follows));
    } catch {}
  };

  const submitFollow = async (form, slug) => {
    const input = form.elements.email;
    const button = form.querySelector("button[type=submit]");
    const email = String(input.value || "").trim();
    const honeypot = String(form.elements.website?.value || "").trim();
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
        body: JSON.stringify({ action: "follow", email, slug, hp: honeypot, reader_id: readerId() }),
      });
      if (response.ok) {
        if (!honeypot) {
          markEmailFollow(slug);
          capture("follow_email_success", { slug });
        }
        input.disabled = true;
        button.remove();
        form.querySelectorAll(".subscribe-inline-note").forEach((note) => note.remove());
        setMessage(form, "✓ We’ll email you when this story moves.", "ok");
        return;
      }
      setMessage(
        form,
        response.status === 400
          ? "Please enter a valid email address."
          : "Email follows are temporarily unavailable. Please try again shortly.",
        "err",
      );
    } catch {
      setMessage(form, "Network error. Check your connection and try again.", "err");
    }
    button.disabled = false;
  };

  const buildFollowForm = (slug) => {
    formSeq += 1;
    const id = `followEmail${formSeq}`;
    const form = document.createElement("form");
    form.className = "subscribe-inline follow-email";
    form.noValidate = true;
    form.innerHTML = `
      <p class="subscribe-inline-kicker">Email alert · this story only</p>
      <label class="subscribe-inline-label" for="${id}">Email address for alerts about this story</label>
      <div class="subscribe-inline-row">
        <input id="${id}" type="email" name="email" required placeholder="you@example.com" autocomplete="email" inputmode="email" />
        <input type="text" name="website" class="subscribe-inline-hp" tabindex="-1" autocomplete="off" aria-hidden="true" />
        <button type="submit">Email me</button>
      </div>
      <p class="subscribe-inline-note">Sent only when it gets new coverage · unfollow from any alert</p>
      <p class="subscribe-inline-msg" role="status" aria-live="polite" hidden></p>`;
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      submitFollow(form, slug);
    });
    return form;
  };

  const enhanceFollowEmail = async () => {
    const slot = document.querySelector("[data-follow-email]");
    const slug = String(slot?.dataset.followEmail || "");
    if (!slot || !SLUG_RE.test(slug)) return;
    if (!inlineEnabled(await loadConfig())) return;
    let form = null;
    const paint = () => {
      const followed = !!readJson(FOLLOWS_KEY)[slug];
      const emailed = !!readJson(EMAIL_FOLLOWS_KEY)[slug];
      if (emailed && !form) {
        slot.textContent = "✓ You’ll get an email when this story moves.";
        slot.classList.add("follow-email-done");
        slot.hidden = !followed;
        return;
      }
      if (followed && !form) {
        form = buildFollowForm(slug);
        slot.replaceChildren(form);
        observeView(form, slug, "follow_email_view", { slug });
      }
      slot.hidden = !followed;
    };
    paint();
    // The storyline page's own Follow script toggles the browser follow first.
    document.getElementById("followBtn")?.addEventListener("click", () => setTimeout(paint, 0));
  };

  const start = () => {
    enhance();
    enhanceFollowEmail();
    // The feed renders its finish marker client-side and re-renders on every
    // filter change, so enhance CTAs as they appear.
    if ("MutationObserver" in window && document.body) {
      new MutationObserver(() => {
        if (document.querySelector(CTA_SELECTOR)) enhance();
      }).observe(document.body, { childList: true, subtree: true });
    }
  };

  window.llmDigestSubscribeInline = { enhance, inlineEnabled };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
