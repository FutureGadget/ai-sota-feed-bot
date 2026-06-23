(() => {
  "use strict";

  const root = document.documentElement;
  if (root.classList.contains("site-chrome-enhanced")) return;

  const chrome = document.querySelector(".site-chrome");
  const nav = chrome?.querySelector(".site-nav-fallback");
  const actions = chrome?.querySelector(".site-actions-fallback");
  const browseButton = chrome?.querySelector("[data-site-browse-open]");
  const moreButton = chrome?.querySelector("[data-site-more-open]");

  if (
    !chrome ||
    !nav ||
    !actions ||
    !browseButton ||
    !moreButton ||
    typeof HTMLDialogElement === "undefined"
  ) {
    return;
  }

  const parentSection = (pathname) => {
    if (pathname === "/" || pathname.startsWith("/story/")) return "/";
    if (pathname === "/daily" || pathname.startsWith("/daily/")) return "/daily";
    if (pathname === "/weekly" || pathname.startsWith("/weekly/")) return "/weekly";
    if (pathname === "/storylines" || pathname.startsWith("/storyline/")) return "/storylines";
    if (pathname === "/playbook" || pathname.startsWith("/playbook/")) return "/playbook";
    if (pathname === "/map" || pathname.startsWith("/topic/")) return "/map";
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

  const groupNavigation = () => {
    const groups = [
      ["Catch up", ["/", "/daily", "/weekly"]],
      ["Follow", ["/storylines"]],
      ["Build", ["/playbook", "/map"]],
      ["More", ["/voices", "/subscribe"]],
    ];
    groups.forEach(([label, destinations]) => {
      const section = document.createElement("section");
      section.className = "site-nav-group";
      const heading = document.createElement("p");
      heading.className = "site-nav-group-label";
      heading.textContent = label;
      const links = document.createElement("div");
      links.className = "site-nav-group-links";
      destinations.forEach((destination) => {
        const link = nav.querySelector(`[data-site-destination="${destination}"]`);
        if (link) links.append(link);
      });
      section.append(heading, links);
      nav.append(section);
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
      trigger.focus();
    });
    return dialog;
  };

  createDialog({
    className: "site-browse-dialog",
    title: "Browse LLM Digest",
    trigger: browseButton,
    content: nav,
  });

  if (actions.children.length) {
    createDialog({
      className: "site-actions-dialog",
      title: "More actions",
      trigger: moreButton,
      content: actions,
    });
  } else {
    moreButton.hidden = true;
  }

  root.classList.add("site-chrome-enhanced");
})();
