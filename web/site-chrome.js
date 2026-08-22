(() => {
  "use strict";

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
    return;
  }

  browseButton.setAttribute("aria-label", "Open Editor's Desk");
  browseButton.innerHTML = '<span class="site-desk-full">Editor\'s Desk</span><span class="site-desk-short">Desk</span>';
  if (moreButton) moreButton.hidden = true;
  if (themeButton) {
    themeButton.classList.add("site-theme-toggle");
    themeButton.setAttribute("title", themeButton.getAttribute("aria-label") || "Toggle theme");
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
    if (pathname === "/storylines" || pathname.startsWith("/storyline/")) return "/storylines";
    if (pathname === "/playbook" || pathname.startsWith("/playbook/")) return "/playbook";
    if (pathname === "/map" || pathname.startsWith("/topic/")) return "/map";
    if (pathname === "/foundations" || pathname.startsWith("/foundations/")) return "/foundations";
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
      ["Catch up", ["/", "/daily", "/weekly"]],
      ["Follow", ["/storylines"]],
      ["Apply", ["/playbook"]],
      ["Understand", ["/map", "/foundations"]],
      ["More", ["/voices", "/subscribe"]],
    ];
    const descriptions = {
      "/": "Ranked stories, finite reading",
      "/daily": "What changed today",
      "/weekly": "What you missed this week",
      "/storylines": "Developing stories over time",
      "/playbook": "Actionable engineering lessons",
      "/map": "Essential know-how for production agents",
      "/foundations": "Durable concept explainers",
      "/voices": "Practitioner voices worth following",
      "/subscribe": "Get the brief by email",
    };
    groups.forEach(([label, destinations]) => {
      const section = document.createElement("section");
      section.className = "site-nav-group";
      const heading = document.createElement("p");
      heading.className = "site-nav-group-label";
      heading.textContent = label;
      const links = document.createElement("div");
      links.className = "site-nav-group-links";
      if (label === "More") fallbackLinks = links;
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
    close.textContent = "Close";
    head.append(heading, close);
    panel.append(head, content);
    dialog.append(panel);
    document.body.append(dialog);

    let scrollY = 0;
    const open = () => {
      scrollY = window.scrollY;
      trigger.setAttribute("aria-expanded", "true");
      dialog.showModal();
      root.classList.add("site-dialog-open");
      close.focus();
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
  if (actions && actions.children.length) {
    const section = document.createElement("section");
    section.className = "site-nav-group site-actions-group";
    const heading = document.createElement("p");
    heading.className = "site-nav-group-label";
    heading.textContent = "Settings";
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
    title: "Editor's Desk",
    trigger: browseButton,
    content: deskContent,
  });

  const updateDeskCount = () => {
    const count = nav.querySelectorAll(".nav-update-dot").length;
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
    sr.textContent = ` (${count} new ${count === 1 ? "section" : "sections"})`;
    browseButton.append(sr);
  };
  updateDeskCount();
  new MutationObserver(updateDeskCount).observe(nav, {
    childList: true,
    subtree: true,
  });

  root.classList.add("site-chrome-enhanced");
})();
