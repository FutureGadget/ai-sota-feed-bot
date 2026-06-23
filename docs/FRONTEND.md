# FRONTEND.md

The primary user surface is the website at https://www.llm-digest.com, with
RSS and scheduled email as retention channels.

## Shared site chrome

Every reader-facing page uses the same responsive header contract:

1. compact LLM Digest home link;
2. optional surface-primary action (Feed Search is the current example);
3. visibly labeled Browse control;
4. More actions for page utilities;
5. page title/status;
6. visible date/week/edition context controls where applicable.

Source assets:

- `web/site-chrome.css` — layout, dialogs, safe areas, focus, responsive and
  no-JavaScript behavior
- `web/site-chrome.js` — progressive enhancement, destination grouping,
  current-route state, dialog lifecycle, scroll locking, and focus restoration
- `pipeline/render_static_pages.py` — generated-page header, canonical
  destination registry, parent-route mapping, and static archive controls

The canonical Browse order is Live feed, Daily recap, Weekly recap,
Storylines, Playbook, Knowledge map, Voices, and Email digest. Do not define a
page-specific destination subset or reorder these links.

### Extension rules

- Put global destinations in `.site-nav-fallback`.
- Put secondary page actions in `.site-actions-fallback`.
- Keep primary content controls outside both disclosures.
- Daily, Weekly, and Playbook selectors use `.site-context` with
  Previous/Current/Next controls.
- The fallback navigation must remain usable before JavaScript initializes.
- Shared JavaScript moves existing semantic nodes into native dialogs; it does
  not create the only copy of a link or action.
- Never add horizontal scrolling to global navigation or page actions.
- Generated pages are changed only through `pipeline/render_static_pages.py`.

Product contract:
`docs/product-specs/mobile-site-chrome.md`.
