/* Deterministic motion player for the daily video.
 *
 * window.loadStoryboard(sb) builds every scene once; window.renderAt(t) draws
 * the frame at time t (seconds) as a pure function of t, so the renderer can
 * seek to any frame and the output is reproducible. No timers, no rAF, no
 * Math.random (a seeded PRNG drives the background).
 *
 * Storyboard: {date, scenes: [{type, seconds, ...data}]}. Scene types:
 *   open       {kicker, heading, bullets[]}
 *   highlights {kicker, heading, bullets[]}
 *   stats      {kicker, heading, stats: [{value, prefix, suffix, decimals, label}]}
 *   category   {kicker, heading, dek, stories: [{title, summary, source, stat?}]}
 *   close      {kicker, heading, url}
 * See docs/product-specs/daily-video.md.
 */
(function () {
  "use strict";
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const prog = (t, a, b) => clamp((t - a) / (b - a));
  const E = {
    out: (x) => 1 - Math.pow(1 - x, 3),
    inOut: (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2),
    back: (x) => { const c = 1.70158; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); },
  };
  const $ = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const place = (el, o) => {
    const s = el.style;
    s.opacity = o.o == null ? 1 : o.o;
    s.transform = `translate(${o.x || 0}px,${o.y || 0}px) scale(${o.s == null ? 1 : o.s})`;
  };
  const fmt = (v, dec) => v.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });

  // Kinetic headline: each word slides up out of its own mask, staggered.
  function words(text, cls) {
    const h = $("div", cls);
    const spans = String(text).split(/\s+/).filter(Boolean).map((w) => {
      const m = $("span", "word"); const i = $("span", null, esc(w)); m.appendChild(i); h.appendChild(m); return i;
    });
    return { el: h, run: (t, start = 0, gap = 0.07) => spans.forEach((sp, i) => {
      const p = E.out(prog(t, start + i * gap, start + i * gap + 0.5));
      sp.style.transform = `translateY(${(1 - p) * 110}%)`;
    }) };
  }

  // ---- background: seeded drifting network, drawn from t ----
  const bg = document.getElementById("bg"); const ctx = bg.getContext("2d");
  let seed = 7; const rnd = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296);
  const dots = Array.from({ length: 46 }, () => ({ x: rnd() * 1280, y: rnd() * 720, r: 18 + rnd() * 60, ph: rnd() * 6.28, sp: 0.12 + rnd() * 0.25 }));
  function drawBg(t) {
    ctx.clearRect(0, 0, 1280, 720);
    ctx.strokeStyle = "rgba(98,90,77,0.10)"; ctx.lineWidth = 1;
    const off = (t * 8) % 64;
    for (let x = -off; x < 1280; x += 64) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, 720); ctx.stroke(); }
    for (let y = 0; y < 720; y += 64) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(1280, y); ctx.stroke(); }
    const pts = dots.map((d) => ({ x: d.x + Math.cos(t * d.sp + d.ph) * d.r, y: d.y + Math.sin(t * d.sp * 1.3 + d.ph) * d.r }));
    for (let i = 0; i < pts.length; i++) for (let j = i + 1; j < pts.length; j++) {
      const dx = pts[i].x - pts[j].x, dy = pts[i].y - pts[j].y, d = Math.hypot(dx, dy);
      if (d < 150) { ctx.strokeStyle = `rgba(163,48,28,${0.16 * (1 - d / 150)})`; ctx.beginPath(); ctx.moveTo(pts[i].x, pts[i].y); ctx.lineTo(pts[j].x, pts[j].y); ctx.stroke(); }
    }
    ctx.fillStyle = "rgba(163,48,28,0.35)";
    pts.forEach((p) => { ctx.beginPath(); ctx.arc(p.x, p.y, 2.4, 0, 6.283); ctx.fill(); });
  }

  // ---- scene builders: return {el, update(local, dur)} ----
  const builders = {
    open(d) {
      const el = $("div", "scene");
      const k = $("div", "kicker", esc(d.kicker)); const h = words(d.heading, "h1"); const intro = $("div", "intro");
      const ps = (d.bullets || []).map((b) => { const p = $("p", null, esc(b)); intro.appendChild(p); return p; });
      el.append(k, h.el, intro);
      return { el, update(t) {
        place(k, { o: E.out(prog(t, 0.1, 0.5)), x: (1 - E.out(prog(t, 0.1, 0.5))) * -30 });
        h.run(t, 0.25);
        ps.forEach((p, i) => { const q = E.out(prog(t, 1.2 + i * 0.9, 1.9 + i * 0.9)); place(p, { o: q, y: (1 - q) * 24 }); });
      } };
    },
    highlights(d) {
      const el = $("div", "scene"); const k = $("div", "kicker", esc(d.kicker)); const h = words(d.heading, "h2");
      const rows = (d.bullets || []).map((b, i) => {
        const r = $("div", "hl", `<span class="no">${String(i + 1).padStart(2, "0")}</span><span>${esc(b)}</span>`);
        const f = $("i", "fill"); r.prepend(f); return { r, f };
      });
      el.append(k, h.el); rows.forEach((x) => el.appendChild(x.r));
      return { el, update(t, dur) {
        h.run(t, 0.1);
        const n = rows.length, span = Math.max(dur - 1.2, 1) / n;
        rows.forEach((x, i) => {
          const q = E.out(prog(t, 0.5 + i * 0.18, 1.0 + i * 0.18));
          const active = clamp((t - (0.9 + i * span)) / 0.3) * (1 - clamp((t - (0.9 + (i + 1) * span)) / 0.3));
          place(x.r, { o: (0.45 + 0.55 * active) * q, x: (1 - q) * 60 + active * 10 });
          x.f.style.transform = `scaleY(${active})`;
        });
      } };
    },
    stats(d) {
      const el = $("div", "scene"); const k = $("div", "kicker", esc(d.kicker)); const h = words(d.heading, "h2"); const grid = $("div", "stats");
      const cells = (d.stats || []).map((s) => {
        const c = $("div", "stat"); const num = $("div", "num"); const lab = $("div", "lab", esc(s.label)); c.append(num, lab); grid.appendChild(c); return { c, num, s };
      });
      el.append(k, h.el, grid);
      return { el, update(t) {
        h.run(t, 0.1);
        cells.forEach((x, i) => {
          const q = E.out(prog(t, 0.5 + i * 0.35, 1.0 + i * 0.35)); const cnt = E.out(prog(t, 0.6 + i * 0.35, 1.9 + i * 0.35));
          place(x.c, { o: q, y: (1 - q) * 30 });
          x.num.textContent = `${x.s.prefix || ""}${fmt(x.s.value * cnt, x.s.decimals || 0)}${x.s.suffix || ""}`;
        });
      } };
    },
    category(d) {
      const el = $("div", "scene"); const k = $("div", "kicker", esc(d.kicker)); const h = words(d.heading, "h2"); const dek = $("div", "dek", esc(d.dek || ""));
      const hub = $("div"); hub.id = "hub"; const svgNS = "http://www.w3.org/2000/svg"; const svg = document.createElementNS(svgNS, "svg");
      const node = $("div", "node", `<b>${d.total || (d.stories || []).length}</b>${(d.total || (d.stories || []).length) === 1 ? "STORY" : "STORIES"}`);
      const n = (d.stories || []).length; const gap = 6; const cardH = Math.min(128, (400 - gap * (n - 1)) / Math.max(n, 1)); const yc = (n * (cardH + gap) - gap) / 2; node.style.top = `${yc - 65}px`;
      const items = (d.stories || []).map((s, i) => {
        const card = $("div", "card"); card.style.top = `${i * (cardH + gap)}px`; card.style.height = `${cardH}px`;
        card.innerHTML = `<div class="src">${esc(s.source || "")}</div><div class="t">${esc(s.title)}</div><div class="s">${esc(s.summary || "")}</div>`;
        let badge = null, num = null;
        if (s.stat) { badge = $("div", "badge", `<div class="n"></div><div class="u">${esc(s.stat.unit || "")}</div>`); num = badge.firstChild; card.appendChild(badge); }
        const path = document.createElementNS(svgNS, "path");
        const y = i * (cardH + gap) + cardH / 2; path.setAttribute("d", `M165 ${yc} C 215 ${yc}, 200 ${y}, 250 ${y}`);
        path.setAttribute("fill", "none"); path.setAttribute("stroke", "#a3301c"); path.setAttribute("stroke-width", "2.5"); path.setAttribute("stroke-linecap", "round");
        path.setAttribute("pathLength", "1"); path.setAttribute("stroke-dasharray", "1"); svg.appendChild(path); hub.appendChild(card);
        return { card, path, num, s };
      });
      hub.prepend(svg); hub.appendChild(node); el.append(k, h.el, dek, hub);
      return { el, update(t, dur) {
        h.run(t, 0.1); place(k, { o: E.out(prog(t, 0, 0.4)) }); place(dek, { o: E.out(prog(t, 0.7, 1.3)), y: (1 - E.out(prog(t, 0.7, 1.3))) * 12 });
        const hp = E.back(prog(t, 0.8, 1.4)); place(node, { o: prog(t, 0.8, 1.0), s: hp });
        // cards arrive spread across the narration so the picture tracks the voice
        const span = Math.max(dur - 2.4, 1.2 * n) / Math.max(n, 1);
        items.forEach((x, i) => {
          const t0 = 1.3 + i * span; const q = E.out(prog(t, t0, t0 + 0.55));
          x.path.style.strokeDashoffset = String(1 - E.inOut(prog(t, t0 - 0.1, t0 + 0.5)));
          place(x.card, { o: q, x: (1 - q) * 120 });
          if (x.num) { const c = E.out(prog(t, t0 + 0.3, t0 + 1.4)); x.num.textContent = `${x.s.stat.prefix || ""}${fmt(x.s.stat.value * c, x.s.stat.decimals || 0)}${x.s.stat.suffix || ""}`; }
        });
      } };
    },
    flow(d) {
      const el = $("div", "scene"); const k = $("div", "kicker", esc(d.kicker)); const h = words(d.heading, "h2"); const wrap = $("div", "flows");
      const arrowSvg = '<svg viewBox="0 0 90 24"><path d="M4 12 H78" pathLength="1" stroke-dasharray="1" fill="none" stroke="#a3301c" stroke-width="3" stroke-linecap="round"/><path d="M68 4 L82 12 L68 20" pathLength="1" stroke-dasharray="1" fill="none" stroke="#a3301c" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>';
      const rows = (d.rows || []).map((r) => {
        const row = $("div", "frow"); const lab = $("div", "flabel", esc(r.label || "")); const line = $("div", "fline");
        const n = r.nodes.length; const w = Math.min(280, (1152 - (n - 1) * 90) / n); const parts = [];
        r.nodes.forEach((nd, i) => {
          if (i) { const a = $("div", "farrow", arrowSvg); line.appendChild(a); parts.push({ a, p: [...a.querySelectorAll("path")] }); }
          const b = $("div", "fnode" + (nd.hot ? " hot" : ""), `<div class="ft">${esc(nd.title)}</div>${nd.sub ? `<div class="fs">${esc(nd.sub)}</div>` : ""}`);
          b.style.width = `${w}px`; line.appendChild(b); parts.push({ b });
        });
        row.append(lab, line); wrap.appendChild(row); return { row, lab, parts };
      });
      el.append(k, h.el, wrap);
      return { el, update(t, dur) {
        h.run(t, 0.1); place(k, { o: E.out(prog(t, 0, 0.4)) });
        const per = Math.max((dur - 2.2) / Math.max(rows.length, 1), 3);
        rows.forEach((r, ri) => {
          const t0 = 0.9 + ri * per; place(r.lab, { o: E.out(prog(t, t0 - 0.2, t0 + 0.3)) });
          let step = 0;
          r.parts.forEach((p) => {
            const s = t0 + step * 0.55;
            if (p.b) { const q = E.back(prog(t, s, s + 0.45)); place(p.b, { o: prog(t, s, s + 0.2), s: 0.85 + 0.15 * q, y: (1 - q) * 14 }); step += 1; }
            else { p.p.forEach((pa, pi) => { pa.style.strokeDashoffset = String(1 - E.inOut(prog(t, s - 0.2 + pi * 0.15, s + 0.3 + pi * 0.15))); }); }
          });
        });
      } };
    },
    versus(d) {
      const el = $("div", "scene"); const k = $("div", "kicker", esc(d.kicker)); const h = words(d.heading, "h2"); const grid = $("div", "versus");
      const cols = [d.left, d.right].map((c, ci) => {
        const col = $("div", "vcol" + (c.win ? " win" : "")); col.appendChild($("div", "vt", esc(c.title)));
        const lines = (c.lines || []).map((l) => { const p = $("p", null, esc(l)); col.appendChild(p); return p; }); grid.appendChild(col); return { col, lines, ci };
      });
      const vs = $("div", "vs", "VS"); grid.insertBefore(vs, grid.children[1]); el.append(k, h.el, grid);
      return { el, update(t, dur) {
        h.run(t, 0.1); place(k, { o: E.out(prog(t, 0, 0.4)) });
        cols.forEach((c) => { const t0 = 0.8 + c.ci * Math.max((dur - 2) / 2, 2); const q = E.out(prog(t, t0, t0 + 0.6));
          place(c.col, { o: q, x: (c.ci ? 1 : -1) * (1 - q) * 70 });
          c.lines.forEach((p, i) => { const s = t0 + 0.7 + i * 0.7; const r = E.out(prog(t, s, s + 0.5)); place(p, { o: r, y: (1 - r) * 12 }); }); });
        place(vs, { o: prog(t, 0.6, 0.9), s: E.back(prog(t, 0.6, 1.2)) });
      } };
    },
    bars(d) {
      const el = $("div", "scene"); const k = $("div", "kicker", esc(d.kicker)); const h = words(d.heading, "h2"); const body = $("div", "barsbody"); const list = $("div", "barlist");
      const max = Math.max(...d.items.map((i) => i.value));
      const items = d.items.map((i) => {
        const r = $("div", "brow", `<div class="bl">${esc(i.label)}</div><div class="btrack"><div class="bfill${i.hot ? " hot" : ""}"></div></div><div class="bv"></div><div class="btag">${esc(i.tag || "")}</div>`);
        list.appendChild(r); return { r, fill: r.querySelector(".bfill"), bv: r.querySelector(".bv"), tag: r.querySelector(".btag"), i };
      });
      body.appendChild(list);
      let side = null, num = null;
      if (d.callout) { side = $("div", "bside", `<div class="bn"></div><div class="bc">${esc(d.callout.label)}</div>`); num = side.firstChild; body.appendChild(side); }
      el.append(k, h.el, body);
      return { el, update(t, dur) {
        h.run(t, 0.1); place(k, { o: E.out(prog(t, 0, 0.4)) });
        items.forEach((x, n) => { const s = 0.9 + n * 1.4; const q = E.inOut(prog(t, s, s + 1.1));
          place(x.r, { o: prog(t, s - 0.2, s + 0.2) }); x.fill.style.width = `${Math.max(x.i.value / max * q * 100, q > 0 ? 0.6 : 0)}%`;
          x.bv.textContent = x.i.display ? (q > 0.98 ? x.i.display : "") : ""; place(x.tag, { o: prog(t, s + 1.0, s + 1.4) }); });
        if (side) { const s = 0.9 + items.length * 1.4; const q = E.out(prog(t, s, s + 0.6)); place(side, { o: q, x: (1 - q) * 40 });
          const c = E.out(prog(t, s + 0.2, s + 1.4)); num.textContent = `${d.callout.prefix || ""}${fmt(d.callout.value * c, d.callout.decimals || 0)}${d.callout.suffix || ""}`; }
      } };
    },
    callout(d) {
      const el = $("div", "scene"); const box = $("div", "callbox"); const k = $("div", "kicker", esc(d.kicker)); const h = words(d.heading, "h1"); const sub = $("div", "dek", esc(d.sub || ""));
      const bar = $("div", "callbar"); box.append(bar, k, h.el, sub); el.appendChild(box);
      return { el, update(t) { bar.style.transform = `scaleY(${E.inOut(prog(t, 0, 0.8))})`; place(k, { o: E.out(prog(t, 0.3, 0.7)) }); h.run(t, 0.5); place(sub, { o: E.out(prog(t, 1.6, 2.2)), y: (1 - E.out(prog(t, 1.6, 2.2))) * 14 }); } };
    },
    close(d) {
      const el = $("div", "scene"); const box = $("div", "close");
      const svg = `<svg viewBox="0 0 100 100"><circle id="cc" cx="50" cy="50" r="44" fill="none" stroke="#a3301c" stroke-width="5" pathLength="1" stroke-dasharray="1"/><path id="ck" d="M28 52 L44 68 L74 34" fill="none" stroke="#a3301c" stroke-width="7" stroke-linecap="round" stroke-linejoin="round" pathLength="1" stroke-dasharray="1"/></svg>`;
      const mark = $("div", null, svg); const k = $("div", "kicker", esc(d.kicker)); k.style.marginTop = "22px"; const h = words(d.heading, "h1"); const url = $("div", "url");
      box.append(mark, k, h.el, url); el.appendChild(box);
      const cc = mark.querySelector("#cc"), ck = mark.querySelector("#ck");
      return { el, update(t) {
        cc.style.strokeDashoffset = String(1 - E.inOut(prog(t, 0.1, 0.9))); ck.style.strokeDashoffset = String(1 - E.out(prog(t, 0.7, 1.3)));
        h.run(t, 0.5); const n = Math.floor(clamp((t - 1.4) / 1.1) * d.url.length); url.textContent = d.url.slice(0, n) + (n < d.url.length && Math.floor(t * 3) % 2 ? "▌" : "");
      } };
    },
  };

  let built = [], total = 0, boundaries = [];
  const sub = document.getElementById("sub");
  const wipe = document.getElementById("wipe"), bar = document.getElementById("bar");
  window.loadStoryboard = function (sb) {
    document.getElementById("date").textContent = sb.date || "";
    const root = document.getElementById("scenes"); root.innerHTML = ""; built = []; let t0 = 0;
    sb.scenes.forEach((s) => {
      const b = (builders[s.type] || builders.highlights)(s); root.appendChild(b.el);
      built.push({ b, start: t0, dur: s.seconds, cues: (String(s.narration || "").match(/[^.!?]+[.!?]*/g) || []).map((x) => x.trim()).filter(Boolean) }); t0 += s.seconds; boundaries.push(t0);
    });
    total = t0;
    const ch = document.getElementById("chapters"); ch.innerHTML = "";
    boundaries.slice(0, -1).forEach((x) => { const i = document.createElement("i"); i.style.left = `${(x / total) * 100}%`; ch.appendChild(i); });
    return total;
  };
  window.renderAt = function (t) {
    drawBg(t);
    let idx = built.findIndex((s) => t < s.start + s.dur); if (idx < 0) idx = built.length - 1;
    built.forEach((s, i) => { s.b.el.style.display = i === idx ? "block" : "none"; });
    const s = built[idx], local = t - s.start;
    s.b.update(local, s.dur);
    const fadeOut = 1 - E.inOut(prog(local, s.dur - 0.3, s.dur));
    s.b.el.style.opacity = idx === built.length - 1 ? 1 : fadeOut;
    // red wipe crosses the screen at each scene boundary
    const w = idx === 0 ? 0 : prog(local, 0, 0.55);
    wipe.style.transform = `translateX(${-101 + 202 * E.inOut(w)}%)`;
    const lead = 0.3, span = Math.max(s.dur - lead - 0.4, 1), cues = s.cues;
    const ci = cues.length ? Math.min(cues.length - 1, Math.floor(clamp((local - lead) / span) * cues.length)) : -1;
    sub.textContent = ci >= 0 && local > lead ? cues[ci] : ""; sub.style.opacity = ci >= 0 ? clamp(Math.min(local - lead, s.dur - local) / 0.25) : 0;
    bar.style.width = `${(t / total) * 100}%`;
  };
})();
