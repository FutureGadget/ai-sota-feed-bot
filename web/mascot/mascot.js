/*
 * Bubble Buddy — a portable, modular 3D mascot (WebGL / Three.js).
 *
 * A genuinely 3D cute-and-intelligent character (a bespectacled blue bubble
 * with an idea-antenna) that pops in at random intervals, bobs around, and
 * tucks away again. Decorative and defensive: any failure (no WebGL, blocked
 * CDN, etc.) silently no-ops so the host page is never affected.
 *
 * ── Portability ────────────────────────────────────────────────────────────
 * Three ways to use it — pick whichever fits:
 *
 * 1. Drop-in (zero config). Import the module; a default mascot floats in the
 *    bottom-right corner:
 *        <script type="module" src="/mascot/mascot.js"></script>
 *    Tweak the default via a global BEFORE import, or opt out with `false`:
 *        <script>window.BubbleBuddyConfig = { position: 'bottom-left' };</script>
 *        <script>window.BubbleBuddyConfig = false;</script>  // no auto mascot
 *
 * 2. Declarative — place it ANYWHERE by dropping an anchor element. Each
 *    `[data-bubble-buddy]` on the page gets its own mascot filling that box:
 *        <div data-bubble-buddy style="width:160px;height:200px"></div>
 *        <div data-bubble-buddy data-position="top-right" data-width="120"
 *             data-tips="Hi there|Welcome!"></div>
 *    Supported data-* attrs: position, width, height, offset-x, offset-y,
 *    z-index, autostart, dismissible, storage-key, first-delay, gap-min,
 *    gap-max, dwell-min, dwell-max, tips ("a|b|c"), aria-label.
 *
 * 3. Programmatic — full control via the factory:
 *        import { createBubbleBuddy } from '/mascot/mascot.js';
 *        const buddy = createBubbleBuddy({ mount: '#hero', position: 'fill' });
 *        buddy.appearNow();  // also: .start() .stop() .hide() .destroy()
 *    `window.BubbleBuddy.create(opts)` is the same factory for non-module use.
 *
 * ── Performance contract ───────────────────────────────────────────────────
 *   - Three.js is dynamically imported (shared across instances) only on the
 *     FIRST appearance, so it costs nothing on initial page load.
 *   - The render loop runs only while a buddy is on screen; fully parked
 *     (no rAF, no GPU) between appearances and while the tab is hidden.
 *   - Caps pixel ratio, tiny canvas, fixed/absolute overlay (zero CLS).
 *   - Skips itself under prefers-reduced-motion and remembers a dismissal.
 */

const DEFAULT_THREE_URL = 'https://unpkg.com/three@0.161.0/build/three.module.js';

const DEFAULT_TIPS = [
  '10 minutes a day ✨', 'All caught up? 🫧', 'I remember that story.',
  'Low-hype, promise.', 'Read it. You’re done.', 'New storyline brewing…',
  'Fresh digest is up!', 'No doomscroll here.',
];

const DEFAULTS = {
  mount: null,                 // Element | CSS selector | null (→ document.body)
  position: 'bottom-right',    // bottom-right | bottom-left | top-right | top-left | fill
  offsetX: 18, offsetY: 14,    // px from the chosen corner (ignored for 'fill')
  width: 150, height: 185,     // px (ignored for 'fill' — fills the mount)
  zIndex: 60,
  autostart: true,             // schedule random appearances on its own
  firstDelayMin: 7000, firstDelayMax: 14000,
  gapMin: 50000, gapMax: 110000,
  dwellMin: 6500, dwellMax: 12000,
  enterMs: 950, leaveMs: 700,
  tips: null,                  // array of strings → overrides DEFAULT_TIPS
  dismissible: true,           // show the × and remember the opt-out
  storageKey: 'bubbleBuddy',   // sessionStorage key for the dismissal
  respectReducedMotion: true,
  colors: null,                // partial palette override, e.g. { spark: '#ff5577' }
  threeUrl: DEFAULT_THREE_URL,
  ariaLabel: 'Bubble, the mascot',
};

// --- shared, cross-instance Three.js loader (imported at most once) ----------
let THREE = null;
let threePromise = null;
function loadThree(url) {
  if (THREE) return Promise.resolve(THREE);
  if (!threePromise) {
    threePromise = import(/* @vite-ignore */ url)
      .then((m) => { THREE = m; return m; })
      .catch((e) => { threePromise = null; throw e; });
  }
  return threePromise;
}

// --- pure helpers ------------------------------------------------------------
function rand(a, b) { return a + Math.random() * (b - a); }
function easeOutBack(t) { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); }
function easeInCubic(t) { return t * t * t; }
function now() { return performance.now(); }

/**
 * Create one mascot instance. Returns a small control API; nothing is rendered
 * until the first appearance (auto-scheduled when `autostart`, or `appearNow()`).
 */
export function createBubbleBuddy(userOpts = {}) {
  const opts = Object.assign({}, DEFAULTS, userOpts);

  // per-instance state (was module-level in the old singleton)
  let renderer, scene, camera, buddy, mini = [], pop = [];
  let container, canvas, tip, dismissBtn;
  let raf = 0, lastTip = -1;
  let state = 'hidden';          // hidden | entering | idle | leaving
  let stateAt = 0, dwell = 0, scheduleTimer = 0;
  let blinkAt = 0, blinking = 0, reactUntil = 0;
  let started = false, destroyed = false, wired = false;
  let themeObserver = null, sizeObserver = null, visHandler = null, floatResizeHandler = null;

  const TIPS = (opts.tips && opts.tips.length) ? opts.tips : DEFAULT_TIPS;
  const REDUCED_MOTION = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const isDismissed = () => {
    try { return sessionStorage.getItem(opts.storageKey) === 'off'; } catch { return false; }
  };

  // ---------------------------------------------------------------------------
  // Theme-aware palette (brand defaults; `opts.colors` overrides any key)
  // ---------------------------------------------------------------------------
  function palette() {
    const dark = document.documentElement.getAttribute('data-theme') === 'dark';
    const base = dark
      ? { body: 0x73a2ff, bodyOpacity: 0.78, glow: 0xa6c8ff, gloss: 0xffffff, core: 0x3f7bff,
          foot: 0x5b8def, pupil: 0x0b1326, eye: 0xffffff, iris: 0x2f6bff, mouth: 0x0b1326,
          brow: 0x0b1326, blush: 0xff8fab, frame: 0xe6eeff, spark: 0xffd76b }
      : { body: 0x6aa0ff, bodyOpacity: 0.74, glow: 0xaecdff, gloss: 0xffffff, core: 0x4f8bef,
          foot: 0x4f8bef, pupil: 0x16233f, eye: 0xffffff, iris: 0x2f6bff, mouth: 0x16233f,
          brow: 0x16233f, blush: 0xff9ab0, frame: 0x1b2a4a, spark: 0xffc94d };
    return opts.colors ? Object.assign(base, opts.colors) : base;
  }

  // ---------------------------------------------------------------------------
  // DOM scaffolding — positioned per `mount` + `position`
  // ---------------------------------------------------------------------------
  function resolveMount() {
    let m = opts.mount;
    if (typeof m === 'string') m = document.querySelector(m);
    return m || document.body;
  }

  function buildDom() {
    const mountEl = resolveMount();
    const toBody = mountEl === document.body;
    const fill = opts.position === 'fill';

    container = document.createElement('div');
    container.className = 'bubble-buddy';
    container.setAttribute('aria-hidden', 'true');
    container.style.cssText = [
      'pointer-events:none', 'display:none',
      `z-index:${opts.zIndex}`,
      'filter:drop-shadow(0 10px 16px rgba(30,58,138,.22))',
    ].join(';');
    container.style.position = toBody ? 'fixed' : 'absolute';
    if (!toBody && getComputedStyle(mountEl).position === 'static') mountEl.style.position = 'relative';

    if (fill) {
      container.style.inset = '0';
      container.style.width = '100%';
      container.style.height = '100%';
    } else {
      container.style.width = opts.width + 'px';
      container.style.height = opts.height + 'px';
      const vert = opts.position.includes('top') ? 'top' : 'bottom';
      const horz = opts.position.includes('left') ? 'left' : 'right';
      container.style[vert] = opts.offsetY + 'px';
      // Horizontal anchoring: when floating fixed-to-viewport (toBody), iOS
      // Safari opens a phantom horizontal scroll gutter for `position: fixed`
      // elements anchored with `right` (made worse by `user-scalable=no`). The
      // mascot then parks itself in that blank space on the right. Anchor with
      // `left`, computed against the clipped viewport width and kept in sync on
      // resize/orientation, so it stays on-screen and never opens a gutter.
      if (toBody && horz === 'right') {
        container.style.right = 'auto';
        floatResizeHandler = () => {
          if (!container) return;
          const vw = document.documentElement.clientWidth || window.innerWidth || 0;
          container.style.left = Math.max(0, Math.round(vw - opts.width - opts.offsetX)) + 'px';
        };
        floatResizeHandler();
        ['resize', 'orientationchange'].forEach((e) => window.addEventListener(e, floatResizeHandler, { passive: true }));
        if (window.visualViewport) window.visualViewport.addEventListener('resize', floatResizeHandler, { passive: true });
      } else {
        container.style[horz] = opts.offsetX + 'px';
      }
    }

    canvas = document.createElement('canvas');
    canvas.style.cssText = 'width:100%;height:100%;display:block;pointer-events:auto;cursor:pointer';
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', opts.ariaLabel);
    container.appendChild(canvas);

    tip = document.createElement('div');
    tip.style.cssText = [
      'position:absolute', 'left:50%', 'top:-6px', 'transform:translate(-50%,-100%) scale(.8)',
      'transform-origin:bottom center', 'background:var(--card,#fff)', 'color:var(--fg,#1a1a1a)',
      'border:1px solid var(--border,#e5e5e5)', 'border-radius:12px', 'padding:6px 11px',
      'font:600 12.5px/1.3 system-ui,-apple-system,Segoe UI,Roboto,sans-serif',
      'white-space:nowrap', 'box-shadow:0 4px 14px rgba(0,0,0,.12)',
      'opacity:0', 'transition:opacity .2s ease, transform .2s ease', 'pointer-events:none',
    ].join(';');
    container.appendChild(tip);

    if (opts.dismissible) {
      dismissBtn = document.createElement('button');
      dismissBtn.textContent = '×';
      dismissBtn.title = 'Hide the mascot for now';
      dismissBtn.setAttribute('aria-label', 'Hide the mascot');
      dismissBtn.style.cssText = [
        'position:absolute', 'right:2px', 'top:2px', 'width:20px', 'height:20px',
        'border:none', 'border-radius:50%', 'background:var(--card,#fff)', 'color:var(--muted,#6b7280)',
        'font:700 14px/1 system-ui', 'cursor:pointer', 'pointer-events:auto',
        'box-shadow:0 1px 5px rgba(0,0,0,.18)', 'opacity:0', 'transition:opacity .15s ease', 'padding:0',
      ].join(';');
      container.addEventListener('mouseenter', () => { dismissBtn.style.opacity = '1'; });
      container.addEventListener('mouseleave', () => { dismissBtn.style.opacity = '0'; });
      dismissBtn.addEventListener('click', dismiss);
      container.appendChild(dismissBtn);
    }

    canvas.addEventListener('click', onPoke);
    mountEl.appendChild(container);

    // Live re-tint on theme flips.
    themeObserver = new MutationObserver(() => { if (buddy) applyPalette(); });
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  }

  function dismiss() {
    try { sessionStorage.setItem(opts.storageKey, 'off'); } catch {}
    clearTimeout(scheduleTimer);
    stopLoop();
    if (container) container.style.display = 'none';
    state = 'hidden';
  }

  // ---------------------------------------------------------------------------
  // Three.js scene
  // ---------------------------------------------------------------------------
  function makeFresnelMaterial(color) {
    return new THREE.ShaderMaterial({
      uniforms: { glowColor: { value: new THREE.Color(color) }, power: { value: 2.4 } },
      vertexShader:
        'varying vec3 vN; varying vec3 vP;' +
        'void main(){ vN = normalize(normalMatrix*normal);' +
        ' vec4 mv = modelViewMatrix*vec4(position,1.0); vP = mv.xyz;' +
        ' gl_Position = projectionMatrix*mv; }',
      fragmentShader:
        'uniform vec3 glowColor; uniform float power; varying vec3 vN; varying vec3 vP;' +
        'void main(){ vec3 v = normalize(-vP);' +
        ' float f = pow(1.0 - max(dot(vN, v), 0.0), power);' +
        ' gl_FragColor = vec4(glowColor, clamp(f, 0.0, 1.0)); }',
      transparent: true, blending: THREE.AdditiveBlending, depthWrite: false,
    });
  }

  function buildBuddy() {
    const p = palette();
    buddy = new THREE.Group();
    const ud = buddy.userData;

    // Body — the big squishy bubble, a touch wider than tall (chubby).
    const bodyMat = new THREE.MeshPhysicalMaterial({
      color: p.body, transparent: true, opacity: p.bodyOpacity,
      roughness: 0.08, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.1, ior: 1.4,
    });
    bodyMat.userData.role = 'body';
    const body = new THREE.Mesh(new THREE.SphereGeometry(1, 64, 64), bodyMat);
    body.scale.set(1.05, 0.96, 1.02);
    buddy.add(body);

    // Inner glow core — gives the bubble depth so it doesn't read hollow/ghostly.
    const coreMat = new THREE.MeshBasicMaterial({ color: p.core, transparent: true, opacity: 0.32, depthWrite: false, blending: THREE.AdditiveBlending });
    coreMat.userData.role = 'core';
    const core = new THREE.Mesh(new THREE.SphereGeometry(0.74, 32, 32), coreMat);
    buddy.add(core);

    // Rim glow — the tell-tale bubble halo.
    const rim = new THREE.Mesh(new THREE.SphereGeometry(1.06, 48, 48), makeFresnelMaterial(p.glow));
    rim.userData.role = 'rim'; rim.scale.set(1.05, 0.96, 1.02);
    buddy.add(rim);

    // Gloss highlight (fake specular spot, upper-left).
    const glossMat = new THREE.MeshBasicMaterial({ color: p.gloss, transparent: true, opacity: 0.9, depthWrite: false });
    const gloss = new THREE.Mesh(new THREE.SphereGeometry(0.2, 24, 24), glossMat);
    gloss.position.set(-0.44, 0.52, 0.74); gloss.scale.set(1, 1.5, 0.35);
    buddy.add(gloss);

    // --- Eyes: BIG, wide-set, LOW on the face (→ big forehead) -------------
    const eyeMat = new THREE.MeshStandardMaterial({ color: p.eye, roughness: 0.18 });
    eyeMat.userData.role = 'eye';
    const irisMat = new THREE.MeshStandardMaterial({ color: p.iris, roughness: 0.25, emissive: p.iris, emissiveIntensity: 0.25 });
    irisMat.userData.role = 'iris';
    const pupilMat = new THREE.MeshStandardMaterial({ color: p.pupil, roughness: 0.15 });
    pupilMat.userData.role = 'pupil';
    const glintMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
    ud.eyes = []; ud.pupils = [];
    for (const sx of [-1, 1]) {
      const eye = new THREE.Group();
      eye.position.set(sx * 0.4, -0.04, 0.72);
      const white = new THREE.Mesh(new THREE.SphereGeometry(0.36, 36, 36), eyeMat);
      white.scale.set(1, 1.18, 0.72);
      // pupil group (iris + dark pupil + sparkles) — drifts to "look around".
      const pg = new THREE.Group();
      pg.position.set(sx * 0.02, -0.01, 0.2);
      const iris = new THREE.Mesh(new THREE.SphereGeometry(0.26, 28, 28), irisMat);
      iris.scale.set(1, 1.05, 0.5);
      const pupil = new THREE.Mesh(new THREE.SphereGeometry(0.17, 24, 24), pupilMat);
      pupil.position.set(0, 0, 0.08); pupil.scale.set(1, 1.05, 0.5);
      const glint = new THREE.Mesh(new THREE.SphereGeometry(0.075, 14, 14), glintMat);
      glint.position.set(sx * 0.09, 0.12, 0.18);
      const glint2 = new THREE.Mesh(new THREE.SphereGeometry(0.04, 12, 12), glintMat);
      glint2.position.set(sx * -0.06, -0.06, 0.18);
      pg.add(iris, pupil, glint, glint2);
      eye.add(white, pg);
      eye.userData.pg = pg; eye.userData.base = pg.position.clone();
      buddy.add(eye);
      ud.eyes.push(eye); ud.pupils.push(pg);
    }

    // --- Eyebrows: small, expressive (raise when curious/poked) ------------
    const browMat = new THREE.MeshStandardMaterial({ color: p.brow, roughness: 0.4 });
    browMat.userData.role = 'brow';
    ud.brows = [];
    for (const sx of [-1, 1]) {
      const brow = new THREE.Mesh(new THREE.CapsuleGeometry(0.04, 0.2, 4, 10), browMat);
      brow.rotation.z = Math.PI / 2 + sx * 0.22;       // slight friendly arch
      brow.position.set(sx * 0.4, 0.34, 0.86);
      brow.userData.baseY = 0.34;
      buddy.add(brow);
      ud.brows.push(brow);
    }

    // --- Glasses: the "smart" cue — round frames + bridge + temples -------
    const frameMat = new THREE.MeshStandardMaterial({ color: p.frame, roughness: 0.3, metalness: 0.7 });
    frameMat.userData.role = 'frame';
    const glasses = new THREE.Group();
    for (const sx of [-1, 1]) {
      const ring = new THREE.Mesh(new THREE.TorusGeometry(0.33, 0.03, 12, 36), frameMat);
      ring.position.set(sx * 0.4, -0.02, 0.92);
      glasses.add(ring);
      const temple = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.5, 8), frameMat);
      temple.rotation.z = Math.PI / 2; temple.rotation.y = sx * 0.5;
      temple.position.set(sx * 0.82, 0.02, 0.55);
      glasses.add(temple);
    }
    const bridge = new THREE.Mesh(new THREE.CylinderGeometry(0.022, 0.022, 0.22, 8), frameMat);
    bridge.rotation.z = Math.PI / 2; bridge.position.set(0, 0.02, 0.94);
    glasses.add(bridge);
    buddy.add(glasses);

    // Blush cheeks.
    const blushMat = new THREE.MeshBasicMaterial({ color: p.blush, transparent: true, opacity: 0.5, depthWrite: false });
    blushMat.userData.role = 'blush';
    for (const sx of [-1, 1]) {
      const cheek = new THREE.Mesh(new THREE.SphereGeometry(0.15, 20, 20), blushMat);
      cheek.position.set(sx * 0.66, -0.36, 0.62); cheek.scale.set(1.2, 0.8, 0.3);
      buddy.add(cheek);
    }

    // Tiny mouth — a small soft smile (opens into a happy grin when poked).
    const mouthMat = new THREE.MeshStandardMaterial({ color: p.mouth, roughness: 0.4 });
    mouthMat.userData.role = 'mouth';
    const mouth = new THREE.Mesh(new THREE.TorusGeometry(0.1, 0.024, 10, 28, Math.PI), mouthMat);
    mouth.position.set(0, -0.5, 0.9); mouth.rotation.z = Math.PI; mouth.scale.set(1, 0.85, 1);
    ud.mouth = mouth;
    buddy.add(mouth);

    // --- Idea antenna: a stalk with a glowing spark on top (intelligence) --
    const footMat = new THREE.MeshStandardMaterial({ color: p.foot, roughness: 0.5 });
    footMat.userData.role = 'foot';
    const stalk = new THREE.Mesh(new THREE.CylinderGeometry(0.022, 0.03, 0.34, 8), footMat);
    stalk.position.set(0.05, 1.12, 0); stalk.rotation.z = -0.12;
    buddy.add(stalk);
    const sparkMat = new THREE.MeshBasicMaterial({ color: p.spark });
    sparkMat.userData.role = 'spark';
    const spark = new THREE.Mesh(new THREE.IcosahedronGeometry(0.12, 0), sparkMat);
    spark.position.set(0.02, 1.34, 0);
    const sparkGlow = new THREE.Mesh(new THREE.SphereGeometry(0.22, 20, 20), makeFresnelMaterial(p.spark));
    sparkGlow.userData.role = 'sparkglow'; sparkGlow.position.copy(spark.position);
    buddy.add(spark, sparkGlow);
    ud.spark = spark; ud.sparkGlow = sparkGlow;

    // Stubby, pigeon-toed feet.
    for (const sx of [-1, 1]) {
      const foot = new THREE.Mesh(new THREE.SphereGeometry(0.26, 24, 24), footMat);
      foot.position.set(sx * 0.34, -0.95, 0.18);
      foot.scale.set(0.85, 0.5, 1.25);
      foot.rotation.y = sx * 0.5; // toes angled inward
      buddy.add(foot);
    }
    // Stubby little arms.
    ud.arms = [];
    for (const sx of [-1, 1]) {
      const arm = new THREE.Mesh(new THREE.SphereGeometry(0.2, 20, 20), footMat);
      arm.position.set(sx * 0.99, -0.3, 0.2); arm.scale.set(0.8, 0.7, 0.8);
      arm.userData.baseY = -0.3;
      buddy.add(arm);
      ud.arms.push(arm);
    }

    // Orbiting gold "thinking" sparkles.
    const miniMat = new THREE.MeshBasicMaterial({ color: p.spark, transparent: true, opacity: 0.9 });
    miniMat.userData.role = 'spark';
    mini = [];
    for (let i = 0; i < 3; i++) {
      const m = new THREE.Mesh(new THREE.IcosahedronGeometry(0.05 + i * 0.015, 0), miniMat.clone());
      m.userData = { ang: Math.random() * Math.PI * 2, r: 1.4 + i * 0.16, sp: 0.35 + i * 0.16, yb: 0.25 + i * 0.12, tw: Math.random() * 6 };
      buddy.add(m);
      mini.push(m);
    }

    buddy.scale.setScalar(0.001);
    scene.add(buddy);
  }

  // Re-tint every material that carries a role tag (theme switch / color override).
  function applyPalette() {
    const p = palette();
    scene.traverse((o) => {
      const m = o.material; if (!m) return;
      const role = m.userData && m.userData.role;
      if (role === 'body') { m.color.set(p.body); m.opacity = p.bodyOpacity; }
      else if (role === 'core') m.color.set(p.core);
      else if (role === 'rim') m.uniforms.glowColor.value.set(p.glow);
      else if (role === 'sparkglow') m.uniforms.glowColor.value.set(p.spark);
      else if (role === 'eye') m.color.set(p.eye);
      else if (role === 'iris') { m.color.set(p.iris); m.emissive.set(p.iris); }
      else if (role === 'pupil') m.color.set(p.pupil);
      else if (role === 'brow') m.color.set(p.brow);
      else if (role === 'frame') m.color.set(p.frame);
      else if (role === 'spark') m.color.set(p.spark);
      else if (role === 'mouth') m.color.set(p.mouth);
      else if (role === 'foot') m.color.set(p.foot);
      else if (role === 'blush') m.color.set(p.blush);
    });
  }

  async function ensureScene() {
    if (renderer) return true;
    if (!window.WebGLRenderingContext) return false;
    try { await loadThree(opts.threeUrl); } catch { return false; }
    if (destroyed) return false;
    if (!container) buildDom();

    const w = container.clientWidth || opts.width, h = container.clientHeight || opts.height;
    renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
    renderer.setSize(w, h, false);

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(34, w / h, 0.1, 100);
    camera.position.set(0, 0.12, 6.0);
    camera.lookAt(0, 0.06, 0);

    scene.add(new THREE.AmbientLight(0xffffff, 0.85));
    const key = new THREE.DirectionalLight(0xffffff, 1.1); key.position.set(-2, 3, 3); scene.add(key);
    const fill = new THREE.DirectionalLight(0xbcd4ff, 0.5); fill.position.set(3, -1, 2); scene.add(fill);

    buildBuddy();

    sizeObserver = new ResizeObserver(() => {
      if (!renderer) return;
      const cw = container.clientWidth, ch = container.clientHeight;
      if (!cw || !ch) return;
      renderer.setSize(cw, ch, false);
      camera.aspect = cw / ch; camera.updateProjectionMatrix();
    });
    sizeObserver.observe(container);

    if (!wired) {
      wired = true;
      visHandler = () => { if (document.hidden) stopLoop(); else if (state !== 'hidden') startLoop(); };
      document.addEventListener('visibilitychange', visHandler);
    }
    return true;
  }

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------
  async function appear() {
    if (destroyed) return;
    if (document.hidden) { scheduleTimer = setTimeout(appear, 8000); return; }
    const ok = await ensureScene();
    if (!ok || destroyed) return; // give up quietly — no retries, no noise
    container.style.display = 'block';
    applyPalette();
    dwell = rand(opts.dwellMin, opts.dwellMax);
    setState('entering');
    blinkAt = now() + rand(1500, 4000);
    startLoop();
  }

  function setState(s) { state = s; stateAt = now(); }

  function scheduleNext() {
    clearTimeout(scheduleTimer);
    if (!destroyed) scheduleTimer = setTimeout(appear, rand(opts.gapMin, opts.gapMax));
  }

  function startLoop() { if (!raf && !destroyed) raf = requestAnimationFrame(tick); }
  function stopLoop() { if (raf) { cancelAnimationFrame(raf); raf = 0; } }

  function onPoke() {
    if (state === 'hidden' || state === 'leaving') return;
    reactUntil = now() + 650;
    spawnPop();
    showTip();
  }

  function showTip() {
    if (!TIPS.length) return;
    let i = Math.floor(Math.random() * TIPS.length);
    if (i === lastTip && TIPS.length > 1) i = (i + 1) % TIPS.length;
    lastTip = i;
    tip.textContent = TIPS[i];
    tip.style.opacity = '1';
    tip.style.transform = 'translate(-50%,-100%) scale(1)';
    clearTimeout(tip._t);
    tip._t = setTimeout(() => {
      tip.style.opacity = '0';
      tip.style.transform = 'translate(-50%,-100%) scale(.8)';
    }, 2600);
  }

  function spawnPop() {
    const p = palette();
    for (let i = 0; i < 6; i++) {
      const gold = i % 2 === 0;
      const mat = new THREE.MeshBasicMaterial({ color: gold ? p.spark : p.glow, transparent: true, opacity: 0.9 });
      const b = new THREE.Mesh(new THREE.IcosahedronGeometry(rand(0.06, 0.13), 0), mat);
      b.position.set(rand(-0.5, 0.5), rand(0, 0.6), rand(0.4, 0.9));
      b.userData = { vy: rand(1.0, 1.8), vx: rand(-0.5, 0.5), life: 1 };
      buddy.add(b); pop.push(b);
    }
  }

  function tick() {
    raf = 0;
    if (destroyed) return;
    const t = now();
    const dt = 1 / 60;

    // entering / leaving scale + position
    if (state === 'entering') {
      const k = Math.min((t - stateAt) / opts.enterMs, 1);
      const s = easeOutBack(k);
      buddy.scale.setScalar(Math.max(0.001, s));
      buddy.position.y = (1 - k) * -1.4;
      if (k >= 1) { setState('idle'); }
    } else if (state === 'leaving') {
      const k = Math.min((t - stateAt) / opts.leaveMs, 1);
      const s = 1 - easeInCubic(k);
      buddy.scale.setScalar(Math.max(0.001, s));
      buddy.position.y = -1.4 * easeInCubic(k);
      if (k >= 1) {
        container.style.display = 'none';
        stopLoop(); setState('hidden');
        if (opts.autostart) scheduleNext();
        return;
      }
    } else if (state === 'idle') {
      if (t - stateAt > dwell) setState('leaving');
    }

    // idle life: bob, sway, breathe, blink, react
    const ph = t / 1000;
    const react = t < reactUntil;
    if (state === 'idle' || state === 'entering') {
      const baseY = state === 'idle' ? 0 : buddy.position.y;
      const bob = Math.sin(ph * 1.8) * 0.06;
      buddy.position.y = baseY + (state === 'idle' ? bob : 0);
      buddy.rotation.z = Math.sin(ph * 1.1) * 0.06;
      buddy.rotation.y = Math.sin(ph * 0.7) * 0.18;
      // squishy breathing (+ a happy squash when poked)
      const squash = react ? 0.12 * Math.sin((reactUntil - t) / 650 * Math.PI * 3) : 0;
      const breathe = Math.sin(ph * 1.8) * 0.02;
      buddy.scale.x = 1 - breathe + squash * 0.6;
      buddy.scale.y = 1 + breathe - squash;
      buddy.scale.z = 1 - breathe + squash * 0.6;
    }

    const ud = buddy.userData;

    // blink + pupil drift ("looking around" → alert/intelligent)
    if (ud.eyes) {
      if (!blinking && t > blinkAt) { blinking = t; }
      let ey = 1;
      if (blinking) {
        const bk = (t - blinking) / 130;
        if (bk >= 1) { blinking = 0; blinkAt = t + rand(2200, 5200); }
        else ey = Math.abs(Math.cos(bk * Math.PI)); // 1→0→1
      }
      for (const eye of ud.eyes) eye.scale.y = Math.max(0.08, ey);

      const dx = react ? 0 : Math.sin(ph * 0.5) * 0.05;
      const dy = react ? 0.02 : Math.sin(ph * 0.37) * 0.035;
      for (let i = 0; i < ud.pupils.length; i++) {
        const pg = ud.pupils[i], base = ud.eyes[i].userData.base;
        pg.position.x = base.x + dx;
        pg.position.y = base.y + dy;
        pg.scale.setScalar(react ? 1.12 : 1);
      }
    }

    // eyebrows: gentle bob; pop up when curious/poked
    if (ud.brows) {
      for (const b of ud.brows) {
        const lift = react ? 0.12 : Math.sin(ph * 1.5) * 0.015;
        b.position.y = b.userData.baseY + lift;
      }
    }

    // mouth: opens into a happy grin on poke
    if (ud.mouth) ud.mouth.scale.set(react ? 1.35 : 1, react ? 1.4 : 0.85, 1);

    // arms: little wave when reacting
    if (ud.arms) {
      for (let i = 0; i < ud.arms.length; i++) {
        const a = ud.arms[i];
        a.position.y = a.userData.baseY + (react ? 0.18 + Math.sin(ph * 22) * 0.06 : 0);
      }
    }

    // idea antenna spark: steady twinkle pulse, brighter on poke
    if (ud.spark) {
      const pulse = 1 + Math.sin(ph * 3) * 0.15 + (react ? 0.4 : 0);
      ud.spark.scale.setScalar(pulse);
      ud.spark.rotation.y += dt * 1.2; ud.spark.rotation.x += dt * 0.6;
      if (ud.sparkGlow) ud.sparkGlow.scale.setScalar(pulse * 1.05);
    }

    // orbiting thinking-sparkles
    for (const m of mini) {
      m.userData.ang += m.userData.sp * dt;
      m.position.set(
        Math.cos(m.userData.ang) * m.userData.r,
        0.3 + Math.sin(ph * 1.2 + m.userData.ang) * m.userData.yb,
        Math.sin(m.userData.ang) * m.userData.r * 0.5 + 0.2,
      );
      m.material.opacity = 0.5 + 0.5 * Math.abs(Math.sin(ph * 2 + m.userData.tw));
      m.rotation.y += dt * 2;
    }

    // pop particles
    for (let i = pop.length - 1; i >= 0; i--) {
      const b = pop[i];
      b.position.y += b.userData.vy * dt;
      b.position.x += b.userData.vx * dt;
      b.userData.life -= dt * 1.4;
      b.material.opacity = Math.max(0, b.userData.life * 0.5);
      b.scale.setScalar(Math.max(0.01, b.userData.life));
      if (b.userData.life <= 0) { buddy.remove(b); b.geometry.dispose(); b.material.dispose(); pop.splice(i, 1); }
    }

    renderer.render(scene, camera);
    if (state !== 'hidden' && !document.hidden) raf = requestAnimationFrame(tick);
  }

  // ---------------------------------------------------------------------------
  // Public instance API
  // ---------------------------------------------------------------------------
  function start() {
    if (started || destroyed) return api;
    if (opts.respectReducedMotion && REDUCED_MOTION) return api;
    if (opts.dismissible && isDismissed()) return api;
    started = true;
    const boot = () => { if (!destroyed) scheduleTimer = setTimeout(appear, rand(opts.firstDelayMin, opts.firstDelayMax)); };
    if ('requestIdleCallback' in window) requestIdleCallback(boot, { timeout: 3000 });
    else setTimeout(boot, 1500);
    return api;
  }

  function stop() { clearTimeout(scheduleTimer); stopLoop(); return api; }

  function destroy() {
    if (destroyed) return;
    destroyed = true;
    clearTimeout(scheduleTimer); stopLoop();
    if (visHandler) document.removeEventListener('visibilitychange', visHandler);
    if (floatResizeHandler) {
      ['resize', 'orientationchange'].forEach((e) => window.removeEventListener(e, floatResizeHandler));
      if (window.visualViewport) window.visualViewport.removeEventListener('resize', floatResizeHandler);
    }
    if (themeObserver) themeObserver.disconnect();
    if (sizeObserver) sizeObserver.disconnect();
    if (scene) scene.traverse((o) => {
      if (o.geometry) o.geometry.dispose();
      const m = o.material; if (m) (Array.isArray(m) ? m : [m]).forEach((x) => x.dispose());
    });
    if (renderer) { renderer.dispose(); if (renderer.forceContextLoss) renderer.forceContextLoss(); }
    if (container && container.parentNode) container.parentNode.removeChild(container);
    renderer = scene = camera = buddy = container = canvas = null;
    mini = []; pop = [];
  }

  const api = {
    /** Force the mascot to appear right now (ignores reduced-motion/dismissal). */
    appearNow: () => { appear(); return api; },
    /** Begin auto-scheduling random appearances (respects reduced-motion + dismissal). */
    start,
    /** Cancel the schedule and park the render loop (keeps the scene for reuse). */
    stop,
    /** Gracefully retreat off-screen if currently visible. */
    hide: () => { if (state === 'idle' || state === 'entering') setState('leaving'); return api; },
    /** Tear everything down: DOM, GPU resources, listeners. */
    destroy,
    /** Current lifecycle state: 'hidden' | 'entering' | 'idle' | 'leaving'. */
    getState: () => state,
    /** The root container element (or null before first appearance / after destroy). */
    get el() { return container; },
    options: opts,
  };

  if (opts.autostart) start();
  return api;
}

export default createBubbleBuddy;

// ---------------------------------------------------------------------------
// Convenience layer: global handle + declarative/auto mounting
// ---------------------------------------------------------------------------
function readDataOpts(el) {
  const d = el.dataset, o = {};
  if (d.position) o.position = d.position;
  if (d.width) o.width = +d.width;
  if (d.height) o.height = +d.height;
  if (d.offsetX) o.offsetX = +d.offsetX;
  if (d.offsetY) o.offsetY = +d.offsetY;
  if (d.zIndex) o.zIndex = +d.zIndex;
  if (d.autostart) o.autostart = d.autostart !== 'false';
  if (d.dismissible) o.dismissible = d.dismissible !== 'false';
  if (d.storageKey) o.storageKey = d.storageKey;
  if (d.firstDelay) { o.firstDelayMin = o.firstDelayMax = +d.firstDelay; }
  if (d.gapMin) o.gapMin = +d.gapMin;
  if (d.gapMax) o.gapMax = +d.gapMax;
  if (d.dwellMin) o.dwellMin = +d.dwellMin;
  if (d.dwellMax) o.dwellMax = +d.dwellMax;
  if (d.ariaLabel) o.ariaLabel = d.ariaLabel;
  if (d.tips) o.tips = d.tips.split('|').map((s) => s.trim()).filter(Boolean);
  return o;
}

function autoMount() {
  if (window.__bubbleBuddyMounted) return;
  window.__bubbleBuddyMounted = true;
  const instances = [];
  const anchors = document.querySelectorAll('[data-bubble-buddy]');
  if (anchors.length) {
    // Place a mascot inside each anchor element (fills its box by default).
    anchors.forEach((el) => {
      const o = readDataOpts(el);
      o.mount = el;
      if (!o.position) o.position = 'fill';
      instances.push(createBubbleBuddy(o));
    });
  } else if (window.BubbleBuddyConfig !== false) {
    // No anchors → the classic single floating mascot (configurable / opt-out).
    instances.push(createBubbleBuddy(window.BubbleBuddyConfig || {}));
  }
  window.BubbleBuddy.instances = instances;
}

if (typeof window !== 'undefined') {
  window.BubbleBuddy = window.BubbleBuddy || {};
  window.BubbleBuddy.create = createBubbleBuddy;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', autoMount);
  else autoMount();
}
