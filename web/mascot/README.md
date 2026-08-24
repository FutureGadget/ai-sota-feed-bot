# Bubble Buddy — portable 3D mascot

A self-contained, dependency-light WebGL (Three.js) mascot: a cute-and-intelligent
bespectacled blue bubble that pops in at random, bobs around, and tucks away.
Decorative and defensive — any failure (no WebGL, blocked CDN) silently no-ops.

It's **one file** (`mascot.js`) you can drop anywhere. Three usage modes:

## 1. Drop-in (default floating mascot)

```html
<script type="module" src="/mascot/mascot.js"></script>
```

A single mascot floats in the bottom-right corner. Configure or disable it with a
global set **before** the module runs:

```html
<script>window.BubbleBuddyConfig = { position: 'bottom-left', width: 120 };</script>
<script>window.BubbleBuddyConfig = false;</script> <!-- no auto mascot -->
```

> On viewports ≤640px, the drop-in mascot scales down (92×114) and mounts with
> `interactive: false` — purely decorative, `pointer-events: none`, no dismiss ×,
> larger safe-area-aware corner offsets — so it never competes with the page's
> taps on small screens. Set `width`/`height`/`interactive` explicitly (or use
> an anchor) to opt out of this default; appearance timing is unchanged either way.

> On this site the module is lazy-loaded on idle via a small `<script type="module">`
> in each page's footer (and in `pipeline/render_static_pages.py` for generated pages),
> so it never touches initial load. See those snippets for the exact pattern.

## 2. Declarative — place it anywhere

Drop an anchor element wherever you want a mascot. Each `[data-bubble-buddy]` on the
page gets its own instance filling that box:

```html
<div data-bubble-buddy style="width:160px;height:200px"></div>

<div data-bubble-buddy
     data-position="top-right" data-width="120" data-height="150"
     data-tips="Hi there|Welcome back|Need a hand?"
     data-dismissible="false"></div>
```

Supported `data-*` attributes: `position`, `width`, `height`, `offset-x`, `offset-y`,
`z-index`, `interactive`, `autostart`, `dismissible`, `storage-key`, `first-delay`,
`gap-min`, `gap-max`, `dwell-min`, `dwell-max`, `tips` (`"a|b|c"`), `aria-label`.

If **any** anchor exists, the default floating mascot is **not** created — the page
fully controls placement.

## 3. Programmatic — full control

```js
import { createBubbleBuddy } from '/mascot/mascot.js';

const buddy = createBubbleBuddy({
  mount: '#hero',        // Element or CSS selector; default = document.body
  position: 'fill',      // 'fill' | bottom-right | bottom-left | top-right | top-left
  autostart: false,      // don't self-schedule; we'll drive it
  tips: ['You're all caught up ✨'],
  colors: { spark: '#ff5fa2' },   // partial palette override (any key)
});

buddy.appearNow();   // summon now (e.g. on a "caught up" event)
buddy.start();       // begin random auto-appearances
buddy.stop();        // cancel schedule, park the render loop
buddy.hide();        // retreat off-screen if visible
buddy.destroy();     // remove DOM + free GPU resources + listeners
buddy.getState();    // 'hidden' | 'entering' | 'idle' | 'leaving'
buddy.el;            // root container element (null before first appear / after destroy)
```

`window.BubbleBuddy.create(opts)` is the same factory for non-module pages, and
`window.BubbleBuddy.instances` holds the auto-mounted instances.

## Options

| Option | Default | Notes |
|---|---|---|
| `mount` | `null` (→ `body`) | Element or selector to attach into. |
| `position` | `'bottom-right'` | Corner, or `'fill'` to fill the mount box. |
| `offsetX` / `offsetY` | `18` / `14` | px from the corner (any CSS length, e.g. a `calc()` with `env(safe-area-inset-*)`; ignored for `fill`). |
| `width` / `height` | `150` / `185` | px (ignored for `fill`). |
| `zIndex` | `60` | |
| `interactive` | `true` | Poke-to-react + dismiss ×. `false`: canvas gets `pointer-events: none`, no ×, no pointer cursor — pure decoration; appearance timers unchanged. |
| `autostart` | `true` | Self-schedule random appearances. |
| `firstDelayMin/Max` | `7000` / `14000` | ms before first appearance. |
| `gapMin/Max` | `50000` / `110000` | ms quiet time between appearances. |
| `dwellMin/Max` | `6500` / `12000` | ms it lingers per appearance. |
| `tips` | brand lines | Speech-bubble lines shown on poke. |
| `dismissible` | `true` | Show the × and remember the opt-out. |
| `storageKey` | `'bubbleBuddy'` | sessionStorage key for the dismissal. |
| `respectReducedMotion` | `true` | Skip auto-start under `prefers-reduced-motion`. |
| `colors` | `null` | Partial palette override, e.g. `{ body, iris, spark, frame, ... }`. |
| `threeUrl` | self-hosted `/mascot/vendor/three.module.min.js` (pinned r161) | Where to import Three.js from. |
| `ariaLabel` | `'Bubble, the mascot'` | Canvas a11y label. |

## Performance & behavior

- Three.js (~150 KB) is imported **once, shared across instances**, only on the first
  appearance — zero cost on initial page load.
- The render loop runs only while a mascot is on screen; parked (no rAF/GPU) between
  appearances and while the tab is hidden.
- Fixed/absolute overlay added post-load → no layout shift (CLS).
- Theme-aware: re-tints live when `document.documentElement[data-theme]` changes.
- Multiple instances are fine (each owns its own WebGL context — keep it to a few;
  browsers cap concurrent contexts).
