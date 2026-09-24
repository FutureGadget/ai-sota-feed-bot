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

  const observeView = (form, placement) => {
    const record = () => {
      if (viewed.has(placement)) return;
      viewed.add(placement);
      capture("subscribe_form_view", { placement, surface: "inline" });
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

  const buildForm = (placement) => {
    formSeq += 1;
    const id = `subscribeInlineEmail${formSeq}`;
    const form = document.createElement("form");
    form.className = "subscribe-inline";
    form.noValidate = true;
    form.dataset.subscribePlacement = placement;
    form.innerHTML = `
      <label class="subscribe-inline-label" for="${id}">Email address</label>
      <div class="subscribe-inline-row">
        <input id="${id}" type="email" name="email" required placeholder="you@example.com" autocomplete="email" inputmode="email" />
        <input type="text" name="website" class="subscribe-inline-hp" tabindex="-1" autocomplete="off" aria-hidden="true" />
        <button type="submit">Subscribe</button>
      </div>
      <p class="subscribe-inline-note">Daily brief + weekly recap. Unsubscribe anytime ·
        <a href="/subscribe" data-subscribe-channel="email" data-subscribe-placement="${placement}_options">weekly only</a></p>
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
      const form = buildForm(placement);
      link.insertAdjacentElement("afterend", form);
      link.hidden = true;
      observeView(form, placement);
    });
  };

  const start = () => {
    enhance();
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
