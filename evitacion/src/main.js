/* Motor de animación determinista: render(t) dibuja el cuadro exacto del
   segundo t. tools/render.mjs lo llama cuadro a cuadro y tools/audio.py usa
   las mismas marcas (window.__cues) para que cada sonido caiga en su cuadro. */
(() => {
  'use strict';

  const DUR = 60;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const lerp = (a, b, t) => a + (b - a) * t;
  const E = {
    lin: t => t,
    outExpo: t => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t)),
    outCubic: t => 1 - Math.pow(1 - t, 3),
    inCubic: t => t * t * t,
    inQuad: t => t * t,
    inOutCubic: t => (t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
    inOutQuart: t => (t < .5 ? 8 * t ** 4 : 1 - Math.pow(-2 * t + 2, 4) / 2),
    inOutSine: t => -(Math.cos(Math.PI * t) - 1) / 2,
    outBack: t => { const c1 = 1.9, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); },
  };
  const P = (t, s, d, e = E.outExpo) => e(clamp((t - s) / d));
  const rand = seed => { let s = (seed * 9301 + 49297) % 2147483647; return () => (s = (s * 16807) % 2147483647) / 2147483647; };
  const f1 = n => n.toFixed(1);

  // ---------------------------------------------------------------- trazos a mano
  function smooth(pts, closed = false) {
    const n = pts.length;
    const at = i => (closed ? pts[(i + n) % n] : pts[clamp(i, 0, n - 1)]);
    let d = `M${f1(pts[0][0])},${f1(pts[0][1])}`;
    for (let i = 0; i < (closed ? n : n - 1); i++) {
      const p0 = at(i - 1), p1 = at(i), p2 = at(i + 1), p3 = at(i + 2);
      d += `C${f1(p1[0] + (p2[0] - p0[0]) / 6)},${f1(p1[1] + (p2[1] - p0[1]) / 6)} ` +
           `${f1(p2[0] - (p3[0] - p1[0]) / 6)},${f1(p2[1] - (p3[1] - p1[1]) / 6)} ${f1(p2[0])},${f1(p2[1])}`;
    }
    return d + (closed ? 'Z' : '');
  }
  const poly = pts => 'M' + pts.map(p => `${f1(p[0])},${f1(p[1])}`).join(' L');

  // subrayado de ida y vuelta, como se hace con un marcador
  function underline(x0, x1, y, seed) {
    const r = rand(seed), j = a => (r() - .5) * 2 * a, pts = [];
    for (let i = 0; i <= 6; i++) { const u = i / 6; pts.push([lerp(x0 - 14, x1 + 10, u), y + lerp(7, -8, u) + j(3)]); }
    for (let i = 1; i <= 3; i++) { const u = i / 3; pts.push([lerp(x1 + 2, x0 + 90, u), y + lerp(-1, 13, u) + j(3)]); }
    return smooth(pts);
  }
  // tachado: un trazo apenas inclinado que se pasa un poco de la palabra
  function strike(x0, x1, y, seed) {
    const r = rand(seed), j = a => (r() - .5) * 2 * a;
    return smooth([[x0 - 16, y + 6 + j(2)], [lerp(x0, x1, .35), y + 1 + j(3)], [lerp(x0, x1, .7), y - 2 + j(3)], [x1 + 16, y - 7 + j(2)]]);
  }
  function arrow(x0, y0, x1, y1, bend, seed) {
    const r = rand(seed), j = a => (r() - .5) * 2 * a;
    const L = Math.hypot(x1 - x0, y1 - y0), nx = -(y1 - y0) / L, ny = (x1 - x0) / L;
    const cx = (x0 + x1) / 2 + nx * bend, cy = (y0 + y1) / 2 + ny * bend, pts = [];
    for (let i = 0; i <= 8; i++) {
      const u = i / 8, a = (1 - u) ** 2, b = 2 * u * (1 - u), c = u * u, k = i && i < 8 ? 1 : 0;
      pts.push([a * x0 + b * cx + c * x1 + k * j(1.5), a * y0 + b * cy + c * y1 + k * j(1.5)]);
    }
    const q = pts[7], ang = Math.atan2(y1 - q[1], x1 - q[0]), h = 24;
    return smooth(pts) +
      ` L${f1(x1 - h * Math.cos(ang - .5))},${f1(y1 - h * Math.sin(ang - .5))} L${f1(x1)},${f1(y1)}` +
      ` L${f1(x1 - h * Math.cos(ang + .5))},${f1(y1 - h * Math.sin(ang + .5))}`;
  }
  // mancha de resaltador: un cuadrilátero torcido con bordes que no cierran parejo
  function highlight(w, h, seed) {
    const r = rand(seed), j = a => (r() - .5) * 2 * a, pts = [];
    for (let i = 0; i <= 5; i++) pts.push([lerp(0, w, i / 5) + j(3), j(4) + (i / 5) * -3]);
    for (let i = 5; i >= 0; i--) pts.push([lerp(0, w, i / 5) + j(3), h + j(5) - (i / 5) * 4]);
    return smooth(pts, true);
  }

  // rectángulo de un elemento en coordenadas de layout de `root` (ignora transforms)
  function localRect(el, root) {
    let x = 0, y = 0, n = el;
    while (n && n !== root) { x += n.offsetLeft; y += n.offsetTop; n = n.offsetParent; }
    return { x, y, w: el.offsetWidth, h: el.offsetHeight };
  }

  // separa un bloque en palabras (los elementos hijos, como <em>, cuentan como una palabra)
  function splitWords(el) {
    const units = [];
    for (const ch of [...el.childNodes]) {
      if (ch.nodeType === 3) {
        const frag = document.createDocumentFragment();
        for (const p of ch.textContent.split(/(\s+)/)) {
          if (!p) continue;
          if (/^\s+$/.test(p)) { frag.appendChild(document.createTextNode(' ')); continue; }
          const s = document.createElement('span');
          s.className = 'w'; s.textContent = p;
          frag.appendChild(s); units.push(s);
        }
        el.replaceChild(frag, ch);
      } else if (ch.nodeType === 1 && ch.tagName !== 'BR') {
        ch.classList.add('w'); units.push(ch);
      }
    }
    return units;
  }

  // ---------------------------------------------------------------- la curva del malestar
  // Mundo del gráfico: x en píxeles (se desplaza con PAN), v = malestar de 0 a 10.
  const G = { y0: 1400, k: 58, pan: 850 };
  const Yv = v => G.y0 - G.k * v;
  const wob = (x, v) => (0.17 * Math.sin(x / 17) + 0.1 * Math.sin(x / 7.3 + 2) + 0.07 * Math.sin(x / 41 + 1)) * (0.35 + 0.09 * v);
  const ss = (a, b, x) => { const u = clamp((x - a) / (b - a)); return u * u * (3 - 2 * u); };
  // episodios: [inicio de la subida, pico (evitás), malestar en el pico, base antes, base después]
  const EP = [
    { a: 150, p: 470, top: 8.0, from: 2.0, to: 1.5, pw: 1.8 },
    { a: 1000, p: 1420, top: 9.3, from: 2.2, to: 2.0, pw: 1.45 },
    { a: 1480, p: 1700, top: 12.5, from: 2.8, to: 3.2, pw: 1.25 },
  ];
  const DROP = 8;
  function V(x) {
    for (let i = 0; i < EP.length; i++) {
      const e = EP[i];
      if (x < e.a) {
        const prev = EP[i - 1];
        if (!prev) return e.from;
        // tramo calmo entre episodios: la ansiedad anticipatoria empieza a subir antes
        const v = lerp(prev.to, e.from, ss(lerp(prev.p + DROP, e.a, .55), e.a, x));
        return v + wob(x, v) * .6;
      }
      if (x <= e.p) { const u = (x - e.a) / (e.p - e.a), v = e.from + (e.top - e.from) * Math.pow(u, e.pw); return v + wob(x, v) * (1 - Math.pow(u, 8)); }
      if (x <= e.p + DROP) return lerp(e.top, e.to, E.inQuad((x - e.p) / DROP));
    }
    const last = EP[EP.length - 1];
    return last.to + wob(x, last.to) * .6;
  }
  // lo que habría pasado si te quedabas: sube un poco, toca techo y baja sola
  function ghostV(x) {
    if (x <= 560) return 8.0 + 0.55 * Math.sin((Math.PI / 2) * (x - 470) / 90);
    return 2.4 + 6.15 * Math.exp(-Math.pow((x - 560) / 205, 1.6));
  }
  // posición de la "punta" del trazo en el tiempo
  const HEAD = [[12.95, 150], [15.62, 470], [15.8, 478], [20, 620], [27.3, 700], [28.5, 1000], [30.6, 1420],
    [30.75, 1428], [31.0, 1480], [32.15, 1700], [32.3, 1708], [35.1, 1850]];
  function headX(t) {
    if (t <= HEAD[0][0]) return HEAD[0][1];
    for (let i = 1; i < HEAD.length; i++) {
      const [t0, x0] = HEAD[i - 1], [t1, x1] = HEAD[i];
      if (t <= t1) return lerp(x0, x1, (t - t0) / (t1 - t0));
    }
    return HEAD[HEAD.length - 1][1];
  }
  const panAt = t => G.pan * P(t, 27.3, 1.3, E.inOutCubic);

  // jorobas de exposición (S8): cada vez el pico es más bajo
  const HUMPS = { x0: 170, w: 195, base: 1.0, A: [6.4, 5.0, 3.7, 2.5], y0: 1390, k: 48, t0: 50.0, dt: 0.8 };
  function humpV(x) {
    const i = Math.floor((x - HUMPS.x0) / HUMPS.w);
    if (i < 0 || i >= HUMPS.A.length) return HUMPS.base;
    const u = (x - HUMPS.x0 - i * HUMPS.w) / HUMPS.w;
    const f = u < .3 ? Math.sin((Math.PI / 2) * u / .3) : Math.exp(-Math.pow((u - .3) / .28, 1.5));
    return HUMPS.base + HUMPS.A[i] * f + 0.06 * Math.sin(x / 9);
  }

  // ---------------------------------------------------------------- S6: el mundo se achica
  // Anillos concéntricos: cada cosa que evitás es una capa de tu mundo que se pierde.
  const WC = { cx: 540, cy: 1092, R: [372, 308, 244, 180, 128, 78] };
  const ITEMS = [
    { txt: 'el plan', top: true, t: 36.45 },
    { txt: 'la reunión', top: false, t: 37.05 },
    { txt: 'el colectivo', top: true, t: 37.65 },
    { txt: 'llamar', top: false, t: 38.25 },
    { txt: 'salir', top: true, t: 38.85 },
  ];
  function worldR(t) {
    let r = WC.R[0] * P(t, 35.25, .6, E.outBack);
    ITEMS.forEach((it, k) => { r = lerp(r, WC.R[k + 1], P(t, it.t + .2, .42, E.outBack)); });
    return Math.max(0, r * (1 - P(t, 40.8, .4, E.inCubic) * .5));
  }

  // ---------------------------------------------------------------- sonido: marcas de tiempo
  // (tools/audio.py las lee de build/cues.json)
  function cues() {
    const c = [
      ['tension', 0], ['marker', 0.3], ['exhale', 0.98], ['meter', 1.02],
      ['swoosh', 2.28], ['beat', 2.42], ['thud', 2.42], ['thud', 2.82], ['thud', 3.2], ['marker', 3.75],
      ['swoosh', 4.6], ['tick', 5.05], ['tick', 5.22], ['thud', 5.42], ['tick', 6.9], ['tick', 8.45], ['marker', 9.45], ['pen', 10.45], ['pen', 11.0],
      ['rise', 12.0], ['pen', 14.0], ['stamp', 15.5], ['drop', 15.62], ['exhale', 15.66], ['pen', 15.95], ['pen', 18.2],
      ['ghost', 21.0], ['pen', 21.1], ['pen', 24.7],
      ['swoosh', 27.3], ['stamp', 30.45], ['drop', 30.6], ['drop', 32.15], ['pen', 32.35], ['alarm', 31.0],
      ['hit', 35.0], ['pop', 35.25],
      ...ITEMS.map(it => ['scratch', it.t]), ...ITEMS.map(it => ['shrink', it.t + .12]),
      ['swoosh', 41.2], ['beep', 42.0], ['printer', 42.15], ['tear', 44.25],
      ['swoosh', 47.1], ['pen', 53.2],
      ...HUMPS.A.map((_, i) => ['hump', HUMPS.t0 + i * HUMPS.dt]),
      ['swoosh', 54.62], ['thud', 55.42], ['thud', 56.42], ['shrinkWord', 56.75], ['pop', 57.15],
    ];
    // malestar (0–10) cada 10 ms mientras la curva se dibuja, para "escucharlo"
    const anx = [];
    for (let t = 0; t <= DUR; t += .01) {
      let v = null;
      if (t >= 12.95 && t < 35.0) v = V(headX(t));
      anx.push(v == null ? -1 : +v.toFixed(3));
    }
    return { cues: c.sort((a, b) => a[1] - b[1]), anx, anxRate: 100, ticket: ROWS_T, humps: { t0: HUMPS.t0, dt: HUMPS.dt, A: HUMPS.A } };
  }
  const ROWS_T = [42.45, 42.8, 43.15, 43.5, 43.95];

  // ---------------------------------------------------------------- estado
  const S = {};

  function init() {
    S.scenes = $$('.scene').map(el => ({ el, id: el.id, s: +el.dataset.start, e: +el.dataset.end, cam: $('.cam', el) }));
    S.scenes.forEach(sc => { sc.el.style.display = 'block'; });

    // palabras
    S.words = [];
    $$('[data-fx="words"]').forEach(el => {
      const t0 = +el.dataset.in, st = +(el.dataset.st || .14);
      splitWords(el).forEach((w, i) => S.words.push({ el: w, t: t0 + i * st }));
    });

    // resaltadores
    S.marks = $$('.hl').map((sp, i) => {
      const ns = 'http://www.w3.org/2000/svg', svg = document.createElementNS(ns, 'svg');
      const w = sp.offsetWidth + 26, h = sp.offsetHeight * .56;
      svg.setAttribute('width', w); svg.setAttribute('height', h + 8);
      svg.style.left = '-14px'; svg.style.top = f1(sp.offsetHeight * .36) + 'px';
      svg.style.mixBlendMode = 'multiply';
      const p = document.createElementNS(ns, 'path');
      p.setAttribute('d', highlight(w, h, 31 + i)); p.setAttribute('fill', '#DCE24B'); p.setAttribute('opacity', '.95');
      p.setAttribute('filter', 'url(#roughSoft)');
      svg.appendChild(p); sp.insertBefore(svg, sp.firstChild);
      return { svg, t: +sp.dataset.mark, d: +(sp.dataset.md || .4) };
    });

    // S6: los ítems del círculo (afuera en tinta, adentro en hueso) y sus tachados
    buildWorld();

    // trazos que dependen del layout
    $$('[data-under]').forEach(p => {
      const r = localRect($(p.dataset.under), p.closest('.cam'));
      p.setAttribute('d', underline(r.x + 6, r.x + r.w - 8, r.y + r.h * .9, +p.dataset.seed));
    });
    $$('[data-strike]').forEach(p => {
      const r = localRect($(p.dataset.strike), p.closest('.cam'));
      p.setAttribute('d', strike(r.x, r.x + r.w - 20, r.y + r.h * .58, +p.dataset.seed));
    });
    $$('[data-arrow]').forEach(p => {
      const [a, b] = p.dataset.arrow.split(' ').map(s => s.split(',').map(Number));
      p.setAttribute('d', arrow(a[0], a[1], b[0], b[1], +(p.dataset.bend || 0), +p.dataset.seed));
    });

    // animaciones declaradas en el HTML
    S.anims = $$('[data-in],[data-out]').filter(el => el.dataset.fx !== 'words' || el.dataset.out).map(el => {
      let fx = el.dataset.fx || (el.classList.contains('in') && el.parentElement.classList.contains('ln') ? 'rise' : 'block');
      if (fx === 'words') fx = 'outonly';
      const a = {
        el, fx,
        tin: fx === 'outonly' || el.dataset.in == null ? null : +el.dataset.in,
        tout: el.dataset.out != null ? +el.dataset.out : null,
        d: +(el.dataset.d || (fx === 'pop' ? .5 : fx === 'rise' ? .7 : .6)),
        dout: +(el.dataset.dout || .38),
      };
      if (fx === 'draw') { a.L = el.getTotalLength(); el.style.strokeDasharray = `${a.L} ${a.L + 10}`; }
      return a;
    });

    S.grain = $$('.grain');
    S.boil = $$('.boil');

    // S1
    S.meterCells = $$('#meter .row i'); S.meterNum = $('#meterNum'); S.hook1 = $('#hook1');
    // gráfico
    S.world = $('#world'); S.worldHtml = $('#worldHtml');
    S.lineMain = $('#lineMain'); S.ghost = $('#ghost'); S.head = $('#head'); S.ticker = $('#ticker');
    S.drops = [$('#drop1'), $('#drop2'), $('#drop3')];
    const ticks = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    ticks.setAttribute('class', 'stroke'); ticks.setAttribute('stroke', '#ECE7DC'); ticks.setAttribute('stroke-width', '4');
    ticks.setAttribute('d', EP.map(e => `M${e.p},1390 L${e.p},1412`).join(' '));
    S.world.insertBefore(ticks, S.world.firstChild);
    // pre-cálculo de la curva
    S.curve = []; for (let x = 150; x <= 1850; x += 3) S.curve.push([x, Yv(V(x))]);
    S.ghostPts = []; for (let x = 470; x <= 952; x += 4) S.ghostPts.push([x, Yv(ghostV(x))]);
    // S7
    S.ticket = $('#ticket'); S.rows = $$('#ticket .tl');
    // S8
    S.humps = $('#humps');
    S.humpPts = []; for (let x = 150; x <= 960; x += 3) S.humpPts.push([x, HUMPS.y0 - HUMPS.k * humpV(x)]);
    // S9
    S.achica = $('#achica');
  }

  function buildWorld() {
    const ns = 'http://www.w3.org/2000/svg', svg = $('#rings');
    const el = (tag, attrs, parent) => {
      const e = document.createElementNS(ns, tag);
      for (const k in attrs) e.setAttribute(k, attrs[k]);
      if (parent) parent.appendChild(e);
      return e;
    };
    const { cx, cy, R } = WC;
    const defs = el('defs', {}, svg);
    const clip = el('clipPath', { id: 'wClip' }, defs);
    S.wClipC = el('circle', { cx, cy, r: 0 }, clip);
    const outer = el('g', {}, svg);
    S.wCircle = el('circle', { cx, cy, r: 0, fill: '#2A3EA5', filter: 'url(#rough)' }, svg);
    const inner = el('g', { 'clip-path': 'url(#wClip)' }, svg);
    // límites entre capas: punteados (tinta afuera, hueso adentro)
    R.forEach((r, k) => {
      if (k > 0) el('circle', { cx, cy, r, class: 'stroke', stroke: '#ECE7DC', 'stroke-width': 2.5, 'stroke-dasharray': '3 12', opacity: .55 }, inner);
      el('circle', { cx, cy, r, class: 'stroke', stroke: '#0F111B', 'stroke-width': 2.5, 'stroke-dasharray': '3 12', opacity: .3 }, outer);
    });
    const arcPath = (r, top) => top
      ? `M${cx - r},${cy} A${r},${r} 0 0 1 ${cx + r},${cy}`
      : `M${cx - r},${cy} A${r},${r} 0 0 0 ${cx + r},${cy}`;
    S.items = ITEMS.map((it, k) => {
      const rIn = R[k + 1], rOut = R[k];
      const rp = it.top ? rIn + 12 : rOut - 12;
      el('path', { id: `arc${k}`, d: arcPath(rp, it.top) }, defs);
      const mk = (g, fill) => {
        const tx = el('text', { fill, stroke: fill, 'text-anchor': 'middle' }, g);
        const tp = el('textPath', { href: `#arc${k}`, startOffset: '50%' }, tx);
        tp.textContent = it.txt;
        return tx;
      };
      const o = mk(outer, '#0F111B'), n = mk(inner, '#ECE7DC');
      // tachado que sigue el arco, a la altura del medio de las letras
      const L = n.getComputedTextLength(), half = L / 2 / rp + .09;
      const rs = it.top ? rp + 17 : rp - 17, mid = it.top ? -Math.PI / 2 : Math.PI / 2;
      const r = rand(70 + k), pts = [];
      for (let i = 0; i <= 8; i++) {
        const u = i / 8, a = it.top ? mid - half + 2 * half * u : mid + half - 2 * half * u;
        const rr = rs + (r() - .5) * 5 + (u - .5) * (it.top ? -8 : 8);
        pts.push([cx + Math.cos(a) * rr, cy + Math.sin(a) * rr]);
      }
      const d = smooth(pts);
      const po = el('path', { d, class: 'stroke', stroke: '#0F111B', 'stroke-width': 7, filter: 'url(#roughSoft)' }, outer);
      const pi = el('path', { d, class: 'stroke', stroke: '#DCE24B', 'stroke-width': 8, filter: 'url(#roughSoft)' }, inner);
      return { ...it, k, o, n, po, pi, L: 0 };
    });
    S.items.forEach(it => { it.L = it.po.getTotalLength(); [it.po, it.pi].forEach(p => { p.style.strokeDasharray = `${it.L} ${it.L + 10}`; }); });
    S.vos = el('text', { x: cx, y: cy + 20, fill: '#DCE24B', stroke: '#DCE24B', 'text-anchor': 'middle', style: 'font-size:76px' }, svg);
    S.vos.textContent = 'vos';
  }

  // ---------------------------------------------------------------- animaciones genéricas
  function generic(t) {
    for (const a of S.anims) {
      const eIn = a.fx === 'pop' ? E.outBack : a.fx === 'write' || a.fx === 'draw' ? E.inOutSine : E.outExpo;
      const pin = a.tin == null ? 1 : P(t, a.tin, a.d, eIn);
      const pout = a.tout == null ? 0 : P(t, a.tout, a.dout, E.inCubic);
      const st = a.el.style;
      switch (a.fx) {
        case 'rise': st.transform = `translateY(${f1((1 - pin) * 150 - pout * 150)}%)`; break;
        case 'block': case 'outonly':
          st.transform = `translateY(${f1((1 - pin) * 50 - pout * 70)}px)`;
          st.opacity = f1(clamp(pin * 1.6) * (1 - pout) * 100) / 100; break;
        case 'fade': st.opacity = f1(pin * (1 - pout) * 100) / 100; break;
        case 'pop':
          st.transform = `scale(${(lerp(.3, 1, pin) * (1 - pout * .3)).toFixed(3)})`;
          st.opacity = clamp(pin * 4) * (1 - pout); break;
        case 'write':
          st.clipPath = `inset(-40% ${f1((1 - pin) * 114 - 12)}% -40% -10%)`;
          st.opacity = 1 - pout; break;
        case 'draw':
          st.strokeDashoffset = f1(a.L * (1 - pin));
          st.opacity = pin > 0 ? 1 - pout : 0; break;
      }
    }
    for (const w of S.words) {
      const p = P(t, w.t, .34, E.outBack);
      w.el.style.transform = `translateY(${f1((1 - p) * 34)}px) scale(${(lerp(.92, 1, clamp(p))).toFixed(3)})`;
      w.el.style.opacity = t < w.t ? 0 : f1(clamp((t - w.t) / .07) * 100) / 100;
    }
    for (const m of S.marks) {
      const p = P(t, m.t, m.d, E.inOutSine);
      m.svg.style.clipPath = `inset(0 ${f1((1 - p) * 100)}% 0 0)`;
    }
  }

  // ---------------------------------------------------------------- escenas
  function s1(t, el) {
    // el primer cuadro ya tiene texto: entra apenas más grande y se asienta
    const k = P(t, 0, .45, E.outCubic);
    S.hook1.style.transform = `translateY(${f1(-P(t, 2.32, .32, E.inCubic) * 70)}px) scale(${(1.05 - .05 * k).toFixed(4)})`;
    S.hook1.style.transformOrigin = '0 0';
    // medidor: 8 casillas encendidas (la última titila) y cae a 2 con el alivio
    const drop = P(t, 1.0, .26, E.inCubic), lit = Math.round(lerp(8, 2, drop));
    const flick = Math.floor(t * 8) % 2;
    S.meterCells.forEach((c, i) => {
      const on = i < lit && !(i === 7 && flick && t < 1);
      c.style.background = on ? (drop > .5 ? 'var(--lima)' : 'var(--hueso)') : 'transparent';
      c.style.borderColor = drop > .5 && i < lit ? 'var(--lima)' : 'var(--hueso)';
      c.style.opacity = on || drop < .5 ? 1 : .45;
    });
    S.meterNum.textContent = `${lit} / 10`;
    S.meterNum.style.color = drop > .5 ? 'var(--lima)' : '';
    // pasa a la escena 2: sube todo
    const out = P(t, 4.62, .44, E.inOutQuart);
    el.querySelector('.cam').style.transform = `translateY(${f1(-out * 520)}px)`;
  }

  function s2(t, el) {
    const p = P(t, 4.62, .44, E.inOutQuart);
    el.style.transform = p < 1 ? `translateY(${f1((1 - p) * 1920)}px)` : 'none';
  }

  function sG(t, el) {
    // entra como un nivel que sube: el malestar llenando la pantalla
    const lv = lerp(1940, -40, P(t, 12.0, .62, E.inOutQuart));
    if (lv > -39) {
      const pts = [];
      for (let x = 0; x <= 1080; x += 40) pts.push(`${x}px ${f1(lv + 16 * Math.sin(x / 70 + t * 9) + 8 * Math.sin(x / 23 - t * 13))}px`);
      el.style.clipPath = `polygon(0 1920px, ${pts.join(', ')}, 1080px 1920px)`;
    } else el.style.clipPath = 'none';
    // de cobalto a noche cuando llega "mañana"
    const n = P(t, 27.3, 1.0, E.inOutSine);
    el.style.background = `rgb(${f1(lerp(42, 15, n))},${f1(lerp(62, 17, n))},${f1(lerp(165, 27, n))})`;

    const pan = panAt(t), hx = headX(t);
    S.world.setAttribute('transform', `translate(${f1(-pan)} 0)`);
    S.worldHtml.style.transform = `translateX(${f1(-pan)}px)`;
    const drawn = t < 12.95 ? [] : S.curve.filter(p => p[0] <= hx);
    if (drawn.length > 1) {
      const last = [hx, Yv(V(hx))];
      S.lineMain.setAttribute('d', poly([...drawn, last]));
      S.head.setAttribute('cx', f1(last[0])); S.head.setAttribute('cy', f1(last[1]));
      S.head.setAttribute('r', hx < 1849 ? 12 : 0);
      const v = V(hx);
      S.ticker.textContent = v.toFixed(1);
      S.ticker.style.left = f1(last[0] - pan + 22) + 'px'; S.ticker.style.top = f1(last[1] - 52) + 'px';
      S.ticker.style.opacity = hx < 1849 ? 1 : 0;
      S.ticker.style.color = (EP.some(e => hx > e.p && hx < e.p + 70)) ? 'var(--lima)' : 'var(--hueso)';
    } else { S.lineMain.setAttribute('d', ''); S.head.setAttribute('r', 0); S.ticker.style.opacity = 0; }
    // caídas de alivio en lima
    EP.forEach((e, i) => {
      const k = clamp((hx - e.p) / DROP);
      S.drops[i].setAttribute('d', k > 0 ? poly([[e.p, Yv(e.top)], [e.p + DROP * k, Yv(V(e.p + DROP * k))]]) : '');
    });
    // lo que no ves: la curva fantasma
    const g = P(t, 21.0, 2.6, E.inOutSine);
    const gx = lerp(470, 952, g);
    const gp = S.ghostPts.filter(p => p[0] <= gx);
    S.ghost.setAttribute('d', g > 0 && gp.length > 1 ? poly([...gp, [gx, Yv(ghostV(gx))]]) : '');
    S.ghost.style.opacity = 1 - P(t, 27.3, .8, E.lin) * .7;
  }

  function s6(t, el) {
    const r = worldR(t);
    S.wCircle.setAttribute('r', f1(r)); S.wClipC.setAttribute('r', f1(r));
    S.items.forEach(it => {
      const p = P(t, it.t, .32, E.inOutSine);
      [it.po, it.pi].forEach(pp => { pp.style.strokeDashoffset = f1(it.L * (1 - p)); pp.style.opacity = p > 0 ? 1 : 0; });
      const show = P(t, 35.55 + it.k * .09, .4, E.outCubic);
      it.n.style.opacity = show;
      it.o.style.opacity = show * (1 - .5 * P(t, it.t + .6, .4, E.lin));
    });
    S.vos.style.opacity = P(t, 35.7, .3, E.lin);
  }

  function s7(t, el) {
    const p = P(t, 41.2, .42, E.inOutQuart);
    el.style.clipPath = p < 1 ? `circle(${f1(p * 2300)}px at ${WC.cx}px ${WC.cy}px)` : 'none';
    // el ticket se imprime: baja de a renglones, con el temblor de la impresora
    const tk = S.ticket, h = tk.offsetHeight;
    const shown = clamp(P(t, 42.1, .25, E.outCubic) * .14 + S.rows.reduce((acc, r, i) => acc + P(t, ROWS_T[i], .22, E.outCubic) * .17, 0));
    const printing = t > 42.1 && t < 44.2;
    const jit = printing ? Math.sin(t * 90) * 1.6 : 0;
    tk.style.clipPath = `inset(0 0 ${f1((1 - shown) * 100)}% 0)`;
    tk.style.transform = `translate(${f1(jit)}px, ${f1(-(1 - shown) * h * .0 + (printing ? Math.abs(jit) : 0))}px) rotate(${f1(-1.8 + P(t, 44.25, .5, E.outBack) * 0.9)}deg)`;
    S.rows.forEach((r, i) => { r.style.opacity = P(t, ROWS_T[i] + .05, .2, E.lin); });
    const out = P(t, 47.1, .5, E.inOutQuart);
    el.querySelector('.cam').style.transform = `translateX(${f1(-out * 420)}px)`;
  }

  function s8(t, el) {
    const p = P(t, 47.1, .5, E.inOutQuart);
    el.style.transform = p < 1 ? `translateX(${f1((1 - p) * 1080)}px)` : 'none';
    // cada exposición: sube, toca su pico y baja sola (cada vez menos)
    let hx = 150;
    if (t > 49.75) hx = lerp(150, HUMPS.x0, P(t, 49.75, .25, E.lin));
    HUMPS.A.forEach((_, i) => { const s = HUMPS.t0 + i * HUMPS.dt; if (t > s) hx = HUMPS.x0 + HUMPS.w * (i + P(t, s, HUMPS.dt, E.inOutSine)); });
    if (t > HUMPS.t0 + HUMPS.A.length * HUMPS.dt) hx = lerp(HUMPS.x0 + HUMPS.w * 4, 950, P(t, HUMPS.t0 + 4 * HUMPS.dt, .4, E.outCubic));
    const pts = S.humpPts.filter(q => q[0] <= hx);
    S.humps.setAttribute('d', t > 49.75 && pts.length > 1 ? poly(pts) : '');
  }

  function s9(t, el) {
    const p = P(t, 54.62, .48, E.inOutQuart);
    el.style.clipPath = p < 1 ? `inset(0 0 ${f1((1 - p) * 100)}% 0)` : 'none';
    // "te achica": la palabra se achica de verdad
    S.achica.style.fontSize = (1 - .48 * P(t, 56.75, .45, E.outBack)).toFixed(3) + 'em';
  }

  const FX = { s1, s2, sG, s6, s7, s8, s9 };

  function render(t) {
    for (const sc of S.scenes) {
      const on = t >= sc.s && t < sc.e;
      sc.el.style.display = on ? 'block' : 'none';
      if (!on) continue;
      if (FX[sc.id]) FX[sc.id](t, sc.el);
      // deriva de cámara muy lenta (salvo en S1, que maneja su propia cámara)
      if (sc.id !== 's1' && sc.id !== 's7') sc.cam.style.transform = `scale(${(1 + .022 * (t - sc.s) / (sc.e - sc.s)).toFixed(4)})`;
    }
    generic(t);
    const gi = Math.floor(t * 12) % S.grain.length;
    S.grain.forEach((g, i) => { g.style.display = i === gi ? 'block' : 'none'; });
    const seed = 1 + (Math.floor(t * 8) % 6);
    S.boil.forEach(b => b.setAttribute('seed', seed));
  }

  window.__ready = (async () => {
    await Promise.all([...document.fonts].map(f => f.load()));
    await document.fonts.ready;
    init();
    render(0);
  })();
  window.__render = render;
  window.__cues = () => cues();
  window.__DUR = DUR;

  const q = new URLSearchParams(location.search);
  window.__ready.then(() => {
    if (q.has('t')) render(+q.get('t'));
    if (q.has('play')) {
      const t0 = performance.now();
      const tick = () => { render(((performance.now() - t0) / 1000) % DUR); requestAnimationFrame(tick); };
      tick();
    }
  });
})();
