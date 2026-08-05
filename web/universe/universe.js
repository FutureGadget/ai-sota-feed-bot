/*
 * Knowledge Universe — the orbital view of the agent know-how wiki (/map).
 *
 * Every planet is a recurring problem area of production agents; the lights on
 * its surface are the topic pages (obstacles + the solutions that address
 * them). Lights you have not read burn bright; pages you have read dim, so the
 * universe literally calms down as you work through it. Planets with recently
 * updated pages ping a radar beacon so returning readers can spot what's new.
 *
 * Read state comes from localStorage ('ai_feed_topic_reads_v1', written by
 * nav-updates.js when a /topic/<slug> page is opened). No accounts, no server.
 *
 * Progressive enhancement, mascot-style defensive: the section it enhances is
 * hidden until this module boots, Three.js is imported from the CDN on demand,
 * and ANY failure (no WebGL, blocked CDN, bad data) re-hides the section and
 * leaves the plain HTML list below as the page. The render loop only runs
 * while the viewport is on screen and the tab is visible; under
 * prefers-reduced-motion it renders only on interaction (no ambient drift).
 */

const THREE_URL = 'https://unpkg.com/three@0.161.0/build/three.module.js';
const READS_KEY = 'ai_feed_topic_reads_v1';
const FRESH_DAYS = 21; // an update within this window counts as "new"

// One hue per orbit slot (assigned by area order, not id, so new areas just
// take the next slot). Tuned for the dark viewport: mid-lightness, distinct.
const PLANET_COLORS = [
  '#63a3ff', '#b78bfa', '#ffcf5c', '#43d6c5', '#7ce38b', '#ff9e64', '#f472b6',
  '#e8c07b', '#6ee7f2', '#c3f25c', '#ff8585', '#9aa7ff', '#f0abfc', '#8fd3ff',
  '#ffd9a0', '#a5f3fc',
];

/* ── tiny utils ──────────────────────────────────────────────────────────── */

function hashStr(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}
function frac(h, salt) { return ((hashStr(salt + h) % 10000) / 10000); }

function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]
  ));
}

function readsMap() {
  try {
    const raw = localStorage.getItem(READS_KEY);
    const obj = raw ? JSON.parse(raw) : null;
    return obj && typeof obj === 'object' ? obj : {};
  } catch { return {}; }
}

function capture(event, props) {
  try {
    if (window.aiFeedPostHog?.capture) window.aiFeedPostHog.capture(event, props);
    else window.posthog?.capture?.(event, props);
  } catch { /* analytics is never load-bearing */ }
}

function updatedMs(topic) {
  if (!topic.updated) return 0;
  const t = Date.parse(`${topic.updated}T00:00:00Z`);
  return Number.isFinite(t) ? t : 0;
}

// read:      opened since its last update — its light is dim.
// badge new: never opened and updated recently.
// badge upd: opened before, but the page moved on since.
function topicState(topic, reads, nowMs) {
  const readTs = Number(reads[topic.slug]) || 0;
  const upd = updatedMs(topic);
  const fresh = upd && nowMs - upd < FRESH_DAYS * 864e5;
  if (readTs && (!upd || readTs >= upd)) return { read: true, badge: null };
  if (readTs) return { read: false, badge: 'updated' };
  return { read: false, badge: fresh ? 'new' : null };
}

/* ── data model: areas + nodes → planets with flat topic lists ───────────── */

function buildPlanets(data) {
  const nodes = data.nodes || {};
  const planets = [];
  for (const area of data.areas || []) {
    const topics = [];
    const seen = new Set();
    for (const oslug of area.obstacles || []) {
      const o = nodes[oslug];
      if (!o || seen.has(oslug)) continue;
      seen.add(oslug);
      const solutions = (o.solutions || []).filter((s) => nodes[s]);
      topics.push({ slug: oslug, ...o, solutions });
      for (const sslug of solutions) {
        if (seen.has(sslug)) continue;
        seen.add(sslug);
        topics.push({ slug: sslug, ...nodes[sslug], solutions: [] });
      }
    }
    if (topics.length) {
      planets.push({ id: area.id || area.label, label: area.label || area.id, topics });
    }
  }
  return planets;
}

/* ── canvas textures (glow, ping ring, text labels) ──────────────────────── */

function glowTexture(THREE) {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d');
  const grad = g.createRadialGradient(64, 64, 2, 64, 64, 64);
  grad.addColorStop(0, 'rgba(255,255,255,.9)');
  grad.addColorStop(0.35, 'rgba(255,255,255,.28)');
  grad.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grad;
  g.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
}

function ringTexture(THREE) {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d');
  g.strokeStyle = 'rgba(255,255,255,.9)';
  g.lineWidth = 5;
  g.beginPath();
  g.arc(64, 64, 56, 0, Math.PI * 2);
  g.stroke();
  return new THREE.CanvasTexture(c);
}

function labelSprite(THREE, lines) {
  // lines: [{text, font, color, pad}] top→bottom, drawn on a 2x canvas.
  const scale = 2;
  const c = document.createElement('canvas');
  const g = c.getContext('2d');
  let w = 0;
  let h = 6;
  for (const l of lines) {
    g.font = l.font;
    w = Math.max(w, g.measureText(l.text).width + 4);
    h += l.size + (l.pad || 0);
  }
  c.width = Math.ceil(w) * scale;
  c.height = Math.ceil(h) * scale;
  g.scale(scale, scale);
  g.textAlign = 'center';
  g.textBaseline = 'top';
  let y = 3;
  for (const l of lines) {
    g.font = l.font;
    g.fillStyle = l.color;
    g.fillText(l.text, c.width / scale / 2, y);
    y += l.size + (l.pad || 0);
  }
  const tex = new THREE.CanvasTexture(c);
  tex.anisotropy = 4;
  const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false });
  const sprite = new THREE.Sprite(mat);
  sprite.userData.aspect = c.width / c.height;
  return sprite;
}

const MONO = '"SFMono-Regular", ui-monospace, Menlo, monospace';

function planetLabel(THREE, planet, state) {
  const unread = state.unread;
  const sub = unread > 0 ? `${unread} unread` : 'explored';
  const subColor = unread > 0 ? 'rgba(255,235,190,.95)' : 'rgba(140,155,175,.85)';
  return labelSprite(THREE, [
    { text: planet.label.toUpperCase(), font: `700 15px ${MONO}`, size: 16, color: 'rgba(232,240,252,.96)', pad: 3 },
    { text: state.fresh > 0 ? `${sub} · ✦ updated` : sub, font: `400 11px ${MONO}`, size: 12, color: subColor },
  ]);
}

/* ── the scene ───────────────────────────────────────────────────────────── */

async function boot(section) {
  const dataEl = document.getElementById('knowledge-universe-data');
  if (!dataEl) throw new Error('no data island');
  const data = JSON.parse(dataEl.textContent);
  const planets = buildPlanets(data);
  if (!planets.length) throw new Error('no planets');

  const stage = section.querySelector('.ku-stage');
  if (!stage) throw new Error('no stage');
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

  const THREE = await import(/* @vite-ignore */ THREE_URL);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  renderer.domElement.className = 'ku-canvas';
  renderer.domElement.setAttribute('tabindex', '0');
  renderer.domElement.setAttribute('role', 'application');
  renderer.domElement.setAttribute(
    'aria-label',
    'Orbit view of agent know-how. Drag to orbit, scroll or pinch to zoom, click a planet to open its topics. The same content is listed below.'
  );
  stage.prepend(renderer.domElement);

  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x070b16, 0.0035);
  const camera = new THREE.PerspectiveCamera(50, 1, 0.5, 900);

  scene.add(new THREE.AmbientLight(0x8899bb, 0.55));
  const sunLight = new THREE.PointLight(0xfff2dd, 1400, 0, 1.8);
  scene.add(sunLight);
  const rim = new THREE.DirectionalLight(0x6688cc, 0.5);
  rim.position.set(-60, 80, -40);
  scene.add(rim);

  const glowTex = glowTexture(THREE);
  const ringTex = ringTexture(THREE);

  // Labels keep a ~constant on-screen size: every frame their world scale is
  // set from camera distance (baseH = world height at reference distance 130).
  const labels = [];
  function registerLabel(sprite, baseH) {
    sprite.userData.baseH = baseH;
    labels.push(sprite);
    return sprite;
  }
  const _lblPos = new THREE.Vector3();
  function rescaleLabels() {
    for (const sprite of labels) {
      if (!sprite.visible) continue;
      sprite.getWorldPosition(_lblPos);
      const d = camera.position.distanceTo(_lblPos);
      const h = Math.min(9, Math.max(1.4, sprite.userData.baseH * (d / 130)));
      sprite.scale.set(h * sprite.userData.aspect, h, 1);
    }
  }

  /* starfield */
  {
    const n = 1100;
    const pos = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const r = 260 + Math.random() * 360;
      const t = Math.random() * Math.PI * 2;
      const p = Math.acos(2 * Math.random() - 1);
      pos[i * 3] = r * Math.sin(p) * Math.cos(t);
      pos[i * 3 + 1] = r * Math.cos(p);
      pos[i * 3 + 2] = r * Math.sin(p) * Math.sin(t);
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const mat = new THREE.PointsMaterial({ color: 0xbfd0ea, size: 1.1, sizeAttenuation: false, transparent: true, opacity: 0.7 });
    scene.add(new THREE.Points(geo, mat));
  }

  /* the sun: your agent in production — everything orbits it */
  {
    const core = new THREE.Mesh(
      new THREE.IcosahedronGeometry(2.6, 2),
      new THREE.MeshBasicMaterial({ color: 0xffe9c4 })
    );
    scene.add(core);
    const halo = new THREE.Sprite(new THREE.SpriteMaterial({
      map: glowTex, color: 0xffd9a0, transparent: true, opacity: 0.85,
      blending: THREE.AdditiveBlending, depthWrite: false,
    }));
    halo.scale.setScalar(22);
    scene.add(halo);
    const cap = labelSprite(THREE, [
      { text: 'YOUR AGENT, IN PRODUCTION', font: `600 11px ${MONO}`, size: 12, color: 'rgba(255,226,178,.9)' },
    ]);
    cap.position.set(0, -6.4, 0);
    scene.add(registerLabel(cap, 2.6));
  }

  /* planets */
  const nowMs = Date.now();
  let reads = readsMap();
  const pickables = [];
  const GOLDEN = Math.PI * (3 - Math.sqrt(5));

  planets.forEach((planet, i) => {
    const color = new THREE.Color(PLANET_COLORS[i % PLANET_COLORS.length]);
    const orbitR = 24 + i * 6.0;
    const angle = i * GOLDEN * 2 + frac(planet.id, 'a') * 0.9;
    const radius = 1.75 + 0.5 * Math.sqrt(planet.topics.length);

    const group = new THREE.Group();
    group.position.set(Math.cos(angle) * orbitR, 0, Math.sin(angle) * orbitR);

    /* orbit ring */
    {
      const pts = [];
      for (let k = 0; k <= 128; k++) {
        const t = (k / 128) * Math.PI * 2;
        pts.push(new THREE.Vector3(Math.cos(t) * orbitR, 0, Math.sin(t) * orbitR));
      }
      const geo = new THREE.BufferGeometry().setFromPoints(pts);
      const ring = new THREE.Line(geo, new THREE.LineBasicMaterial({ color: 0x33415c, transparent: true, opacity: 0.35 }));
      scene.add(ring);
    }

    const body = new THREE.Mesh(
      new THREE.SphereGeometry(radius, 40, 28),
      new THREE.MeshStandardMaterial({
        color, roughness: 0.6, metalness: 0.1,
        emissive: color.clone().multiplyScalar(0.16),
      })
    );
    body.userData.planet = planet;
    group.add(body);
    pickables.push(body);

    /* topic satellites: one per page, circling the planet. Bright = unread. */
    const moons = [];
    const nTopics = planet.topics.length;
    planet.topics.forEach((topic, ti) => {
      const pivot = new THREE.Group();
      // Each satellite gets its own slightly-tilted orbital plane.
      pivot.rotation.x = (frac(topic.slug, 'tx') - 0.5) * 0.7;
      pivot.rotation.z = (frac(topic.slug, 'tz') - 0.5) * 0.5;
      const moon = new THREE.Mesh(
        new THREE.SphereGeometry(Math.max(0.24, radius * 0.15), 12, 10),
        new THREE.MeshBasicMaterial({ transparent: true })
      );
      const mglow = new THREE.Sprite(new THREE.SpriteMaterial({
        map: glowTex, color: 0xffe9bd, transparent: true, opacity: 0,
        blending: THREE.AdditiveBlending, depthWrite: false,
      }));
      mglow.scale.setScalar(Math.max(0.24, radius * 0.15) * 7);
      moon.add(mglow);
      moon.userData = {
        topic,
        planet,
        glow: mglow,
        orbitR: radius * 2.05,
        angle0: (ti / Math.max(1, nTopics)) * Math.PI * 2 + frac(topic.slug, 'ph') * 0.6,
        speed: 0.18 + frac(topic.slug, 'sp') * 0.14,
        baseScale: 1,
      };
      moon.position.set(moon.userData.orbitR, 0, 0);
      pivot.add(moon);
      group.add(pivot);
      moons.push(moon);
      pickables.push(moon);
    });

    /* atmosphere glow — opacity tracks how much is left unread */
    const glow = new THREE.Sprite(new THREE.SpriteMaterial({
      map: glowTex, color, transparent: true,
      blending: THREE.AdditiveBlending, depthWrite: false,
    }));
    glow.scale.setScalar(radius * 5.2);
    group.add(glow);

    /* radar ping for planets holding new/updated pages */
    const ping = new THREE.Sprite(new THREE.SpriteMaterial({
      map: ringTex, color: 0xffe6a8, transparent: true, opacity: 0,
      blending: THREE.AdditiveBlending, depthWrite: false,
    }));
    group.add(ping);

    /* selection ring (shown while the panel is open) */
    const sel = new THREE.Mesh(
      new THREE.TorusGeometry(radius * 1.7, 0.07, 10, 64),
      new THREE.MeshBasicMaterial({ color: 0xe8f0fc, transparent: true, opacity: 0 })
    );
    sel.rotation.x = Math.PI / 2;
    group.add(sel);

    planet.three = { group, body, moons, glow, ping, sel, color, radius, label: null };
    scene.add(group);
  });

  /* satellites hold their orbital position even without the ambient loop */
  function placeMoons(t) {
    for (const planet of planets) {
      for (const moon of planet.three.moons) {
        const u = moon.userData;
        const a = u.angle0 + (reduceMotion ? 0 : t * u.speed);
        moon.position.set(Math.cos(a) * u.orbitR, 0, Math.sin(a) * u.orbitR);
      }
    }
  }

  /* per-planet read-state → materials + labels; safe to re-run on change */
  function applyReadState() {
    reads = readsMap();
    // Solutions can sit on several planets; totals count unique pages once.
    const uniq = new Map();
    for (const planet of planets) {
      for (const t of planet.topics) {
        if (!uniq.has(t.slug)) uniq.set(t.slug, topicState(t, reads, nowMs));
      }
    }
    let totUnread = 0;
    let totFresh = 0;
    const totTopics = uniq.size;
    for (const st of uniq.values()) {
      if (!st.read) totUnread++;
      if (st.badge) totFresh++;
    }
    for (const planet of planets) {
      let unread = 0;
      let fresh = 0;
      for (const moon of planet.three.moons) {
        const st = topicState(moon.userData.topic, reads, nowMs);
        moon.userData.fresh = !!st.badge;
        if (!st.read) unread++;
        if (st.badge) fresh++;
        moon.material.color = st.read
          ? planet.three.color.clone().multiplyScalar(0.38)
          : new THREE.Color(0xfff3d6);
        moon.material.opacity = st.read ? 0.55 : 1;
        moon.userData.glow.material.opacity = st.read ? 0.08 : 0.75;
        moon.userData.baseScale = st.read ? 0.75 : 1.1;
        moon.scale.setScalar(moon.userData.baseScale);
      }
      const total = planet.topics.length;
      const unreadFrac = total ? unread / total : 0;
      planet.three.glow.material.opacity = 0.14 + 0.5 * unreadFrac;
      planet.three.body.material.emissive = planet.three.color.clone()
        .multiplyScalar(0.08 + 0.3 * unreadFrac);
      planet.state = { unread, fresh, total };

      if (planet.three.label) {
        planet.three.label.removeFromParent();
        const i = labels.indexOf(planet.three.label);
        if (i >= 0) labels.splice(i, 1);
      }
      const label = planetLabel(THREE, planet, planet.state);
      label.position.set(0, planet.three.radius + 3.1, 0);
      label.visible = openPlanet !== planet;
      planet.three.group.add(registerLabel(label, 3.1));
      planet.three.label = label;
    }
    const readout = section.querySelector('[data-ku-readout]');
    if (readout) {
      const bits = [`${planets.length} areas`, `${totTopics} pages`, `${totUnread} unread`];
      if (totFresh) bits.push(`✦ ${totFresh} new or updated`);
      readout.textContent = bits.join(' · ');
    }
    needsRender = true;
  }

  /* ── camera + controls ─────────────────────────────────────────────── */

  const view = { theta: -0.85, phi: 1.08, dist: 128, target: new THREE.Vector3(0, 0, 0) };
  const goal = { theta: view.theta, phi: view.phi, dist: view.dist, target: view.target.clone() };
  const homeView = { theta: goal.theta, phi: goal.phi, dist: goal.dist, target: goal.target.clone() };
  let needsRender = true;

  function applyCamera() {
    const st = Math.sin(view.phi);
    camera.position.set(
      view.target.x + view.dist * st * Math.cos(view.theta),
      view.target.y + view.dist * Math.cos(view.phi),
      view.target.z + view.dist * st * Math.sin(view.theta)
    );
    camera.lookAt(view.target);
  }

  const clampPhi = (p) => Math.min(1.45, Math.max(0.2, p));
  const clampDist = (d) => Math.min(230, Math.max(26, d));

  const canvas = renderer.domElement;
  const pointers = new Map();
  let drag = null;
  let pinchBase = 0;

  canvas.addEventListener('pointerdown', (e) => {
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.size === 1) {
      drag = { x: e.clientX, y: e.clientY, moved: 0, t: performance.now() };
    } else if (pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      pinchBase = Math.hypot(a.x - b.x, a.y - b.y) || 1;
      drag = null;
    }
    try { canvas.setPointerCapture(e.pointerId); } catch { /* synthetic/stale pointer */ }
  });

  canvas.addEventListener('pointermove', (e) => {
    const p = pointers.get(e.pointerId);
    if (p) {
      const dx = e.clientX - p.x;
      const dy = e.clientY - p.y;
      p.x = e.clientX; p.y = e.clientY;
      if (pointers.size === 2) {
        const [a, b] = [...pointers.values()];
        const d = Math.hypot(a.x - b.x, a.y - b.y) || 1;
        goal.dist = clampDist(goal.dist * (pinchBase / d));
        pinchBase = d;
        needsRender = true;
        return;
      }
      if (drag) {
        drag.moved += Math.abs(dx) + Math.abs(dy);
        goal.theta += dx * 0.0055;
        goal.phi = clampPhi(goal.phi - dy * 0.0045);
        needsRender = true;
      }
    } else {
      hover(e); // plain mouse move, nothing pressed
    }
  });

  function endPointer(e) {
    const wasDrag = drag;
    pointers.delete(e.pointerId);
    if (pointers.size < 2) pinchBase = 0;
    if (wasDrag && pointers.size === 0) {
      drag = null;
      if (wasDrag.moved < 7 && performance.now() - wasDrag.t < 500) pick(e);
    }
  }
  canvas.addEventListener('pointerup', endPointer);
  canvas.addEventListener('pointercancel', (e) => { pointers.delete(e.pointerId); drag = null; });
  canvas.addEventListener('pointerleave', () => {
    tooltip.hidden = true;
    if (hovered) { hovered = null; needsRender = true; }
  });

  canvas.addEventListener('wheel', (e) => {
    e.preventDefault();
    goal.dist = clampDist(goal.dist * (1 + e.deltaY * 0.0011));
    needsRender = true;
  }, { passive: false });

  canvas.addEventListener('keydown', (e) => {
    const step = 0.12;
    if (e.key === 'ArrowLeft') goal.theta -= step;
    else if (e.key === 'ArrowRight') goal.theta += step;
    else if (e.key === 'ArrowUp') goal.phi = clampPhi(goal.phi - step * 0.6);
    else if (e.key === 'ArrowDown') goal.phi = clampPhi(goal.phi + step * 0.6);
    else if (e.key === '+' || e.key === '=') goal.dist = clampDist(goal.dist * 0.88);
    else if (e.key === '-' || e.key === '_') goal.dist = clampDist(goal.dist * 1.14);
    else if (e.key === 'Escape') { closePanel(); return; }
    else return;
    e.preventDefault();
    needsRender = true;
  });

  /* ── picking, tooltip, panel ───────────────────────────────────────── */

  const raycaster = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  const tooltip = document.createElement('div');
  tooltip.className = 'ku-tooltip';
  tooltip.hidden = true;
  stage.appendChild(tooltip);

  function hitAt(e) {
    const r = canvas.getBoundingClientRect();
    ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    camera.updateMatrixWorld(); // rays must work even before the first render
    raycaster.setFromCamera(ndc, camera);
    const hit = raycaster.intersectObjects(pickables, false)[0];
    if (!hit) return null;
    const u = hit.object.userData;
    return { planet: u.planet, topic: u.topic || null };
  }

  let hovered = null;
  function hover(e) {
    const hit = hitAt(e);
    const key = hit ? (hit.topic ? hit.topic.slug : hit.planet.id) : null;
    if (key !== hovered) {
      hovered = key;
      canvas.style.cursor = hit ? 'pointer' : 'grab';
      needsRender = true;
    }
    if (hit) {
      const r = stage.getBoundingClientRect();
      tooltip.hidden = false;
      tooltip.style.left = `${e.clientX - r.left + 14}px`;
      tooltip.style.top = `${e.clientY - r.top + 6}px`;
      if (hit.topic) {
        const st = topicState(hit.topic, reads, nowMs);
        tooltip.textContent = `${hit.topic.title} — ${st.read ? 'read' : 'unread'}`;
      } else {
        const st = hit.planet.state;
        tooltip.textContent = `${hit.planet.label} — ${st.total} page${st.total === 1 ? '' : 's'}, ${st.unread} unread`;
      }
    } else {
      tooltip.hidden = true;
    }
  }

  const panel = document.createElement('aside');
  panel.className = 'ku-panel';
  panel.hidden = true;
  stage.appendChild(panel);
  let openPlanet = null;
  let restoreView = null;

  function badgeHtml(badge) {
    if (badge === 'new') return '<span class="ku-badge ku-badge-new">NEW</span>';
    if (badge === 'updated') return '<span class="ku-badge ku-badge-upd">UPDATED</span>';
    return '';
  }

  function topicRowHtml(topic, kindLabel, cls) {
    const st = topicState(topic, reads, nowMs);
    const dot = st.read ? 'ku-dot-read' : 'ku-dot-unread';
    const upd = topic.updated ? `<time>${topic.updated}</time>` : '';
    return (
      `<li class="${cls}"><span class="ku-dot ${dot}" aria-hidden="true"></span>` +
      `<div><span class="ku-kind">${kindLabel}</span>` +
      `<a href="/topic/${encodeURIComponent(topic.slug)}" data-ku-topic="${esc(topic.slug)}">${esc(topic.title)}</a>` +
      `<span class="ku-row-meta">${badgeHtml(st.badge)}${upd}</span></div></li>`
    );
  }

  function openPanel(planet) {
    openPlanet = planet;
    const bySlug = new Map(planet.topics.map((t) => [t.slug, t]));
    let rows = '';
    for (const t of planet.topics) {
      if (t.kind !== 'obstacle') continue;
      rows += topicRowHtml(t, 'Obstacle', 'ku-row ku-row-obstacle');
      for (const s of t.solutions || []) {
        if (bySlug.has(s)) rows += topicRowHtml(bySlug.get(s), 'Solved by', 'ku-row ku-row-solution');
      }
    }
    const st = planet.state;
    panel.innerHTML =
      `<header><span class="ku-chip" style="--ku-c:${PLANET_COLORS[planets.indexOf(planet) % PLANET_COLORS.length]}"></span>` +
      `<div><h3>${esc(planet.label)}</h3><p>${st.total - st.unread} of ${st.total} read</p></div>` +
      `<button type="button" class="ku-close" aria-label="Close">×</button></header>` +
      `<ul class="ku-rows">${rows}</ul>` +
      `<footer>Reading a page dims its satellite out here.</footer>`;
    panel.hidden = false;
    panel.querySelector('.ku-close').addEventListener('click', closePanel);
    section.classList.add('ku-has-panel');

    if (!restoreView) {
      restoreView = { theta: goal.theta, phi: goal.phi, dist: goal.dist, target: goal.target.clone() };
    }
    for (const p of planets) if (p.three.label) p.three.label.visible = p !== planet;
    goal.target.copy(planet.three.group.position);
    goal.dist = Math.max(30, planet.three.radius * 11);
    if (stage.clientWidth > 640) {
      // The panel covers the right side — pan the camera right so the focused
      // planet settles in the visible left half.
      const right = new THREE.Vector3(Math.sin(goal.theta), 0, -Math.cos(goal.theta));
      goal.target.addScaledVector(right, goal.dist * 0.22);
    }
    for (const p of planets) p.three.sel.material.opacity = p === planet ? 0.55 : 0;
    needsRender = true;
    capture('universe_planet_open', { area: planet.id, unread: st.unread, fresh: st.fresh });
  }

  function closePanel() {
    if (!openPlanet) return;
    openPlanet = null;
    panel.hidden = true;
    section.classList.remove('ku-has-panel');
    for (const p of planets) {
      p.three.sel.material.opacity = 0;
      if (p.three.label) p.three.label.visible = true;
    }
    if (restoreView) {
      goal.theta = restoreView.theta;
      goal.phi = restoreView.phi;
      goal.dist = restoreView.dist;
      goal.target.copy(restoreView.target);
      restoreView = null;
    }
    needsRender = true;
  }

  panel.addEventListener('click', (e) => {
    const link = e.target.closest('a[data-ku-topic]');
    if (link) capture('universe_topic_click', { slug: link.dataset.kuTopic, area: openPlanet?.id });
  });

  function pick(e) {
    const hit = hitAt(e);
    if (hit) openPanel(hit.planet);
    else closePanel();
  }

  /* HUD buttons: zoom + reset (also the keyboard-free path on touch) */
  {
    const hud = document.createElement('div');
    hud.className = 'ku-hud';
    hud.innerHTML =
      '<button type="button" data-ku-zoom="in" aria-label="Zoom in">+</button>' +
      '<button type="button" data-ku-zoom="out" aria-label="Zoom out">−</button>' +
      '<button type="button" data-ku-reset aria-label="Reset view">⌂</button>';
    stage.appendChild(hud);
    hud.addEventListener('click', (e) => {
      const b = e.target.closest('button');
      if (!b) return;
      if (b.dataset.kuZoom === 'in') goal.dist = clampDist(goal.dist * 0.8);
      else if (b.dataset.kuZoom === 'out') goal.dist = clampDist(goal.dist * 1.25);
      else {
        closePanel();
        goal.theta = homeView.theta; goal.phi = homeView.phi;
        goal.dist = homeView.dist; goal.target.copy(homeView.target);
      }
      needsRender = true;
    });
  }

  /* ── sizing + render loop ──────────────────────────────────────────── */

  function resize() {
    const w = stage.clientWidth;
    const h = stage.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    needsRender = true;
  }
  new ResizeObserver(resize).observe(stage);
  resize();

  let onScreen = true;
  let running = false;
  let rafId = 0;
  let frames = 0;
  new IntersectionObserver((entries) => {
    onScreen = entries[0]?.isIntersecting !== false;
    schedule();
  }, { rootMargin: '80px' }).observe(stage);
  document.addEventListener('visibilitychange', schedule);

  window.addEventListener('storage', (e) => {
    if (e.key === READS_KEY) { applyReadState(); if (openPlanet) openPanel(openPlanet); }
  });

  const clock = new THREE.Clock();

  function frame() {
    rafId = 0;
    const dt = Math.min(clock.getDelta(), 0.05);
    const t = clock.elapsedTime;

    // damped camera
    const k = 1 - Math.exp(-dt * 7);
    view.theta += (goal.theta - view.theta) * k;
    view.phi += (goal.phi - view.phi) * k;
    view.dist += (goal.dist - view.dist) * k;
    view.target.lerp(goal.target, k);
    const settled =
      Math.abs(goal.theta - view.theta) < 1e-3 && Math.abs(goal.phi - view.phi) < 1e-3 &&
      Math.abs(goal.dist - view.dist) < 0.05 && view.target.distanceTo(goal.target) < 0.05;

    if (!reduceMotion) {
      placeMoons(t);
      for (const planet of planets) {
        planet.three.body.rotation.y += dt * 0.12;
        // radar ping on planets with fresh pages
        if (planet.state.fresh > 0) {
          const phase = (t * 0.55 + frac(planet.id, 'p')) % 1;
          planet.three.ping.scale.setScalar(planet.three.radius * (2.4 + phase * 4.2));
          planet.three.ping.material.opacity = 0.55 * (1 - phase);
        }
        for (const moon of planet.three.moons) {
          if (moon.userData.fresh) {
            moon.scale.setScalar(moon.userData.baseScale * (1 + 0.28 * Math.sin(t * 3.2 + moon.userData.angle0 * 7)));
          }
        }
      }
    }

    applyCamera();
    rescaleLabels();
    renderer.render(scene, camera);
    frames++;
    needsRender = false;

    const keepGoing = !reduceMotion || !settled || pointers.size > 0;
    if (keepGoing && onScreen && !document.hidden) rafId = requestAnimationFrame(frame);
    else running = false;
  }

  function schedule() {
    if (running || !onScreen || document.hidden) return;
    if (reduceMotion && !needsRender) return;
    running = true;
    clock.getDelta();
    rafId = requestAnimationFrame(frame);
  }

  if (reduceMotion) {
    // no ambient loop: render when something changes
    const kick = () => { needsRender = true; schedule(); };
    ['pointerdown', 'pointermove', 'wheel', 'keydown'].forEach((ev) =>
      canvas.addEventListener(ev, kick, { passive: true }));
    const origSchedule = schedule;
    setInterval(() => { if (needsRender) origSchedule(); }, 120);
  }

  placeMoons(0);
  applyReadState();
  applyCamera();
  schedule();

  // Console-only debug handle (also used by automated checks).
  window.__kuDebug = {
    get frames() { return frames; },
    get running() { return running; },
    get onScreen() { return onScreen; },
    reduceMotion,
    view, goal, planets,
  };

  return () => { cancelAnimationFrame(rafId); renderer.dispose(); };
}

/* ── entry ───────────────────────────────────────────────────────────────── */

(function init() {
  const section = document.querySelector('[data-knowledge-universe]');
  if (!section) return;
  try {
    section.hidden = false;
    boot(section).catch(() => { section.hidden = true; });
  } catch {
    section.hidden = true;
  }
})();
