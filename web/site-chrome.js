(() => {
  "use strict";

  // UI text comes from the page's dictionary (the global t(), written by
  // pipeline/render_home.py) where the page has one. The English fallback serves
  // pages without it; tests/test_ui_dictionary.py pins every fallback to
  // config/ui/en.json.
  const tr = (key, fallback, vars) => {
    const text = typeof globalThis.t === "function" ? globalThis.t(key) : fallback;
    return vars ? text.replace(/\{(\w+)\}/g, (match, name) => (name in vars ? vars[name] : match)) : text;
  };

  const root = document.documentElement;
  if (root.classList.contains("site-chrome-enhanced")) return;

  const chrome = document.querySelector(".site-chrome");
  const nav = chrome?.querySelector(".site-nav-fallback");
  const actions = chrome?.querySelector(".site-actions-fallback");
  const browseButton = chrome?.querySelector("[data-site-browse-open]");
  const moreButton = chrome?.querySelector("[data-site-more-open]");
  const themeButton = actions?.querySelector("#themeToggle");
  const languageLinks = Array.from(actions?.querySelectorAll("[data-language-link]") || []);
  const visibleLanguageLinks = [];

  if (languageLinks.length) {
    const preferredLanguages = (navigator.languages?.length ? navigator.languages : [navigator.language])
      .filter(Boolean)
      .map((lang) => String(lang).toLowerCase());
    languageLinks.forEach((link) => {
      const locale = String(link.dataset.languageLocale || "").toLowerCase();
      const matches = preferredLanguages.some((lang) => lang === locale || lang.startsWith(`${locale}-`));
      link.hidden = !matches;
      if (matches) visibleLanguageLinks.push(link);
    });
  }

  if (
    !chrome ||
    !nav ||
    !browseButton ||
    typeof HTMLDialogElement === "undefined"
  ) {
    // Not enhancing: show the fallback links site-chrome.css hides pre-boot.
    root.classList.add("site-chrome-static");
    return;
  }

  browseButton.setAttribute("aria-label", tr("chrome.deskOpen", "Open Editor's Desk"));
  const deskFull = document.createElement("span");
  deskFull.className = "site-desk-full";
  deskFull.textContent = tr("chrome.desk", "Editor's Desk");
  const deskShort = document.createElement("span");
  deskShort.className = "site-desk-short";
  deskShort.textContent = tr("chrome.deskShort", "Desk");
  browseButton.replaceChildren(deskFull, deskShort);
  if (moreButton) moreButton.hidden = true;
  if (themeButton) {
    themeButton.classList.add("site-theme-toggle");
    themeButton.setAttribute("title", themeButton.getAttribute("aria-label") || tr("chrome.themeToggle", "Toggle theme"));
    browseButton.before(themeButton);
  }
  visibleLanguageLinks.forEach((link) => {
    link.classList.add("site-bar-language-action");
    browseButton.before(link);
  });

  const parentSection = (pathname) => {
    if (pathname === "/" || pathname.startsWith("/story/")) return "/";
    if (pathname === "/daily" || pathname.startsWith("/daily/")) return "/daily";
    if (pathname === "/weekly" || pathname.startsWith("/weekly/")) return "/weekly";
    if (pathname === "/community" || pathname.startsWith("/community/")) return "/community";
    if (pathname === "/storylines" || pathname.startsWith("/storyline/")) return "/storylines";
    if (pathname === "/playbook" || pathname.startsWith("/playbook/")) return "/playbook";
    if (pathname === "/map" || pathname.startsWith("/topic/")) return "/map";
    if (pathname === "/foundations" || pathname.startsWith("/foundations/")) return "/foundations";
    if (pathname === "/models" || pathname.startsWith("/models/")) return "/models";
    if (pathname === "/voices") return "/voices";
    if (pathname === "/subscribe") return "/subscribe";
    return "";
  };

  const current = chrome.dataset.siteSection || parentSection(window.location.pathname);
  nav.querySelectorAll("[data-site-destination]").forEach((link) => {
    if (link.dataset.siteDestination === current) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  });

  document.addEventListener("click", (event) => {
    const link = event.target.closest("a[data-subscribe-channel]");
    if (!link || event.__llmDigestSubscribeTracked) return;
    event.__llmDigestSubscribeTracked = true;
    try {
      const props = {
        channel: link.dataset.subscribeChannel || null,
        placement: link.dataset.subscribePlacement || null,
      };
      if (window.aiFeedPostHog?.capture) window.aiFeedPostHog.capture("subscribe_click", props);
      else window.posthog?.capture?.("subscribe_click", props);
    } catch {}
  });

  const groupNavigation = () => {
    let fallbackLinks = null;
    const groups = [
      ["catchUp", tr("nav.group.catchUp", "Catch up"), ["/", "/daily", "/weekly", "/community"]],
      ["follow", tr("nav.group.follow", "Follow"), ["/storylines"]],
      ["apply", tr("nav.group.apply", "Apply"), ["/playbook"]],
      ["understand", tr("nav.group.understand", "Understand"), ["/map", "/foundations", "/models", "/skills"]],
      ["more", tr("nav.group.more", "More"), ["/voices", "/subscribe"]],
    ];
    const descriptions = {
      "/": tr("nav.desc.home", "Ranked stories, finite reading"),
      "/daily": tr("nav.desc.daily", "What changed today"),
      "/weekly": tr("nav.desc.weekly", "What you missed this week"),
      "/community": tr("nav.desc.community", "The recaps, retold as threads by the agent"),
      "/storylines": tr("nav.desc.storylines", "Developing stories over time"),
      "/playbook": tr("nav.desc.playbook", "Actionable engineering lessons"),
      "/map": tr("nav.desc.map", "Essential know-how for production agents"),
      "/foundations": tr("nav.desc.foundations", "Durable concept explainers"),
      "/models": tr("nav.desc.models", "Model pricing and capability radar"),
      "/skills": tr("nav.desc.skills", "Agent skills ranked by adoption"),
      "/voices": tr("nav.desc.voices", "Practitioner voices worth following"),
      "/subscribe": tr("nav.desc.subscribe", "Get the brief by email"),
    };
    groups.forEach(([id, label, destinations]) => {
      const section = document.createElement("section");
      section.className = "site-nav-group";
      const heading = document.createElement("p");
      heading.className = "site-nav-group-label";
      heading.textContent = label;
      const links = document.createElement("div");
      links.className = "site-nav-group-links";
      if (id === "more") fallbackLinks = links;
      destinations.forEach((destination) => {
        const link = nav.querySelector(`[data-site-destination="${destination}"]`);
        if (link) {
          const desc = descriptions[destination];
          if (desc && !link.querySelector(".site-nav-desc")) {
            const labelText = link.textContent.trim();
            link.textContent = "";
            const text = document.createElement("span");
            text.className = "site-nav-text";
            text.textContent = labelText;
            const sub = document.createElement("span");
            sub.className = "site-nav-desc";
            sub.textContent = desc;
            link.append(text, sub);
          }
          links.append(link);
        }
      });
      section.append(heading, links);
      nav.append(section);
    });
    const ungrouped = Array.from(nav.querySelectorAll(":scope > a[data-site-destination]"));
    ungrouped.forEach((link) => {
      if (fallbackLinks) fallbackLinks.append(link);
    });
  };
  groupNavigation();

  const createDialog = ({ className, title, trigger, content }) => {
    const dialog = document.createElement("dialog");
    dialog.className = `site-dialog ${className}`;
    const panel = document.createElement("div");
    panel.className = "site-dialog-panel";
    const head = document.createElement("div");
    head.className = "site-dialog-head";
    const heading = document.createElement("h2");
    const headingId = `site-dialog-${className}`;
    heading.id = headingId;
    heading.textContent = title;
    dialog.setAttribute("aria-labelledby", headingId);
    const close = document.createElement("button");
    close.type = "button";
    close.className = "site-dialog-close";
    close.textContent = tr("common.close", "Close");
    head.append(heading, close);
    panel.append(head, content);
    dialog.append(panel);
    document.body.append(dialog);

    // The desk can be taller than the panel (latest updates plus every
    // destination). macOS hides overlay scrollbars, so without a hint the cut
    // menu reads as broken; fade the bottom edge while there is more to scroll.
    const syncScrollHint = () => {
      const scrollable = panel.scrollHeight > panel.clientHeight + 2;
      panel.classList.toggle("is-scrollable", scrollable);
      panel.classList.toggle(
        "at-scroll-end",
        panel.scrollTop + panel.clientHeight >= panel.scrollHeight - 2
      );
    };
    panel.addEventListener("scroll", syncScrollHint, { passive: true });
    window.addEventListener("resize", syncScrollHint, { passive: true });
    requestAnimationFrame(syncScrollHint);

    trigger.setAttribute("aria-haspopup", "dialog");
    trigger.setAttribute("aria-expanded", "false");

    let scrollY = 0;
    const open = () => {
      scrollY = window.scrollY;
      trigger.setAttribute("aria-expanded", "true");
      dialog.showModal();
      root.classList.add("site-dialog-open");
      close.focus();
      requestAnimationFrame(syncScrollHint);
    };
    const shut = () => {
      if (dialog.open) dialog.close();
    };
    trigger.addEventListener("click", open);
    close.addEventListener("click", shut);
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) shut();
    });
    dialog.addEventListener("close", () => {
      root.classList.remove("site-dialog-open");
      window.scrollTo(0, scrollY);
      trigger.setAttribute("aria-expanded", "false");
      trigger.focus();
    });
    return dialog;
  };

  const deskContent = document.createElement("div");
  deskContent.className = "site-desk-content";
  deskContent.append(nav);
  const visibleActions = actions ? Array.from(actions.children).filter((el) => !el.hidden) : [];
  if (visibleActions.length) {
    const section = document.createElement("section");
    section.className = "site-nav-group site-actions-group";
    const heading = document.createElement("p");
    heading.className = "site-nav-group-label";
    heading.textContent = tr("chrome.settings", "Settings");
    section.append(heading, actions);
    deskContent.append(section);
  } else if (actions) {
    // Emptied by the theme-button move above; leftover whitespace text nodes
    // defeat the CSS :empty guard, so the bordered container would render as
    // a stray hairline rule.
    actions.remove();
  }

  createDialog({
    className: "site-browse-dialog",
    title: tr("chrome.desk", "Editor's Desk"),
    trigger: browseButton,
    content: deskContent,
  });

  const updateDeskCount = () => {
    const count = Array.from(nav.querySelectorAll(".nav-update-dot")).reduce((sum, badge) => sum + (Number(badge.textContent) || 0), 0);
    browseButton.querySelector(".site-desk-count")?.remove();
    browseButton.querySelector(".nav-update-sr")?.remove();
    if (!count) return;
    const badge = document.createElement("span");
    badge.className = "site-desk-count";
    badge.textContent = String(count);
    badge.setAttribute("aria-hidden", "true");
    browseButton.append(badge);
    const sr = document.createElement("span");
    sr.className = "nav-update-sr";
    sr.textContent = ` ${count === 1 ? tr("chrome.unreadOne", "({count} new or updated item)", { count }) : tr("chrome.unreadMany", "({count} new or updated items)", { count })}`;
    browseButton.append(sr);
  };
  updateDeskCount();
  new MutationObserver(updateDeskCount).observe(nav, {
    childList: true,
    subtree: true,
  });

  const bar = chrome.querySelector(".site-bar");
  if (bar && "IntersectionObserver" in window) {
    const spacer = document.createElement("div");
    spacer.className = "site-bar-spacer";
    spacer.setAttribute("aria-hidden", "true");
    const sentinel = document.createElement("div");
    sentinel.className = "site-bar-sentinel";
    sentinel.setAttribute("aria-hidden", "true");
    // Keep the original bar in flow until its trailing edge has actually left
    // the viewport. A zero-height sentinel at the top engaged after only a few
    // pixels and covered the still-visible page heading.
    bar.after(spacer, sentinel);
    let resizeFrame = 0;
    const refreshFixedSpacer = () => {
      if (!bar.classList.contains("site-bar-fixed")) return;
      cancelAnimationFrame(resizeFrame);
      resizeFrame = requestAnimationFrame(() => {
        if (!bar.classList.contains("site-bar-fixed")) return;
        // Measure the bar in its current in-flow responsive layout, then put
        // the fixed class back before the browser paints the resized frame.
        bar.classList.remove("site-bar-fixed");
        spacer.style.height = "";
        const flowHeight = bar.offsetHeight;
        spacer.style.height = `${flowHeight}px`;
        bar.classList.add("site-bar-fixed");
      });
    };
    window.addEventListener("resize", refreshFixedSpacer, { passive: true });
    new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        // A sentinel can also be non-intersecting below a short viewport. Only
        // its exit through the top edge means the in-flow bar has been passed.
        const engage = !entry.isIntersecting && entry.boundingClientRect.top < 0;
        if (bar.classList.contains("site-bar-fixed") === engage) return;
        if (engage) {
          spacer.style.height = `${bar.offsetHeight}px`;
          bar.classList.add("site-bar-fixed");
        } else {
          bar.classList.remove("site-bar-fixed");
          spacer.style.height = "";
        }
      },
      { rootMargin: "0px" }
    ).observe(sentinel);
  }

  root.classList.add("site-chrome-enhanced");
})();
