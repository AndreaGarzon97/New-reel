/* Reel "Refuerzo intermitente" — línea de tiempo determinista.
   window.__seek(t) deja el cuadro exacto del segundo t; window.__cues lista
   los eventos sonoros para que la banda de sonido quede sincronizada. */
/* global gsap, SplitText */
(() => {
  'use strict';
  gsap.registerPlugin(SplitText);

  const DUR = 60;
  const NS = 'http://www.w3.org/2000/svg';
  const C = {
    ink: '#15110F', ink2: '#29221D', bone: '#EBE4D7', bone2: '#D8CDBB', wine: '#561320',
    red: '#D93A2B', redInk: '#B92D20', graphite: '#6E655C', ash: '#968D83',
  };
  // comienzo de cada escena (tiempos de negra a 75 bpm: 0,8 s)
  const T = { s1: 0, s2: 4.0, s3: 10.4, s4: 18.4, s5: 24.4, s6: 33.6, s6b: 40.0, s7: 47.2, s8: 54.4, end: DUR };

  const CUES = [];
  const cue = (t, type, o = {}) => CUES.push(Object.assign({ t: +t.toFixed(4), type }, o));

  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const lerp = (a, b, u) => a + (b - a) * u;
  const smooth = u => u * u * (3 - 2 * u);
  const prog = (t, t0, d) => clamp((t - t0) / d);
  const ease = n => gsap.parseEase(n);
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function svg(tag, attrs = {}, parent) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  const pathFrom = pts => pts.length ? 'M' + pts.map(p => p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' L') : '';

  // ------------------------------------------------------------------
  // textura de papel (determinista)
  // ------------------------------------------------------------------
  function paper(dark) {
    const S = 540, cv = document.createElement('canvas');
    cv.width = cv.height = S;
    const g = cv.getContext('2d'), rnd = mulberry32(dark ? 71 : 37);
    const img = g.createImageData(S, S);
    for (let i = 0; i < S * S; i++) {
      const n = rnd();
      const v = dark ? Math.pow(n, 7) * 30 : 255 - Math.pow(n, 5) * 34;
      img.data[i * 4] = img.data[i * 4 + 1] = img.data[i * 4 + 2] = v;
      img.data[i * 4 + 3] = 255;
    }
    g.putImageData(img, 0, 0);
    for (let k = 0; k < 170; k++) {
      const x = rnd() * S, y = rnd() * S, a = rnd() * Math.PI * 2, L = 10 + rnd() * 34;
      g.strokeStyle = dark ? `rgba(255,255,255,${0.025 + rnd() * 0.04})` : `rgba(90,70,50,${0.04 + rnd() * 0.07})`;
      g.lineWidth = 0.6 + rnd() * 0.8;
      for (const ox of [-S, 0, S]) for (const oy of [-S, 0, S]) {
        g.beginPath();
        g.moveTo(x + ox, y + oy);
        g.quadraticCurveTo(x + ox + Math.cos(a) * L * 0.5 + (rnd() - 0.5) * 8, y + oy + Math.sin(a) * L * 0.5 + (rnd() - 0.5) * 8,
          x + ox + Math.cos(a) * L, y + oy + Math.sin(a) * L);
        g.stroke();
      }
    }
    return `url(${cv.toDataURL('image/png')})`;
  }
  document.documentElement.style.setProperty('--paper', paper(false));
  document.documentElement.style.setProperty('--paper-dark', paper(true));

  // ------------------------------------------------------------------
  // cabecera editorial y firma en cada escena
  // ------------------------------------------------------------------
  const HANDLE = '@lic.andreagarzon';
  const rhHTML = l => `<div class="rh"><span>Refuerzo intermitente</span><span class="rh-r">${l}</span></div><div class="rule"></div>`;
  $$('section.scene').forEach(sec => {
    const kind = sec.dataset.chrome, label = sec.dataset.rh || '';
    if (kind === 'split') {
      const a = document.createElement('div');
      a.className = 'chrome on-light';
      a.innerHTML = rhHTML(label);
      $('.panel.top', sec).appendChild(a);
      const b = document.createElement('div');
      b.className = 'chrome on-dark';
      b.innerHTML = `<div class="handle" style="top:${1466 - 960}px">${HANDLE}</div>`;
      $('.panel.bot', sec).appendChild(b);
    } else {
      const c = document.createElement('div');
      c.className = 'chrome ' + (kind === 'light' ? 'on-light' : 'on-dark');
      c.innerHTML = rhHTML(label) + `<div class="handle">${HANDLE}</div>`;
      sec.appendChild(c);
    }
  });

  const tl = gsap.timeline({ paused: true });
  const procs = [];

  const lines = sel => $$(sel + ' .ln > span');
  function reveal(targets, t, o = {}) {
    if (typeof targets === 'string') targets = lines(targets);
    tl.fromTo(targets, { yPercent: 118 }, {
      yPercent: 0, duration: o.d ?? 1.05, ease: o.ease ?? 'expo.out', stagger: o.st ?? 0.085, immediateRender: true,
    }, t);
  }
  function kicker(sel, t, o = {}) {
    reveal(sel, t, Object.assign({ d: 0.9 }, o));
    const sq = $$(sel + ' .sq');
    if (sq.length) tl.fromTo(sq, { scale: 0 }, { scale: 1, duration: 0.5, ease: 'back.out(3)', immediateRender: true }, t + 0.05);
  }
  function exitUp(targets, t, o = {}) {
    if (typeof targets === 'string') targets = lines(targets);
    tl.to(targets, { yPercent: -118, duration: o.d ?? 0.5, ease: o.ease ?? 'power3.in', stagger: o.st ?? 0.035 }, t);
  }
  function fadeIn(targets, t, d = 0.5, from = {}) {
    const to = { autoAlpha: 1, duration: d, ease: 'power2.out', immediateRender: true };
    if ('x' in from) to.x = 0;   // sólo tocar transformaciones si se piden (no pisar rotaciones de SVG)
    if ('y' in from) to.y = 0;
    tl.fromTo(targets, Object.assign({ autoAlpha: 0 }, from), to, t);
  }
  const CLIP0 = { up: 'inset(100% 0% 0% 0%)', down: 'inset(0% 0% 100% 0%)', center: 'inset(50% 0% 50% 0%)' };
  function wipe(target, t, mode = 'up', d = 0.62) {
    tl.fromTo(target, { clipPath: CLIP0[mode] }, { clipPath: 'inset(0% 0% 0% 0%)', duration: d, ease: 'power4.inOut', immediateRender: true }, t);
  }
  function push(id, t0, t1) {
    tl.fromTo(`#${id} > .cam`, { scale: 1 }, { scale: 1.022, duration: t1 - t0, ease: 'none', immediateRender: true }, t0);
  }
  const drift = (id, t, d = 0.62) => tl.to(`#${id} > .cam`, { y: -110, duration: d, ease: 'power3.in' }, t);
  const hideAt = (id, t) => tl.set('#' + id, { visibility: 'hidden' }, t);
  // geometría de un elemento respecto del escenario (antes de animar nada)
  const stageBox = $('#stage').getBoundingClientRect();
  const box = e => { const r = e.getBoundingClientRect(); return { x: r.left - stageBox.left, y: r.top - stageBox.top, w: r.width, h: r.height }; };

  function build() {
    $$('.split').forEach(e => { e._lines = SplitText.create(e, { type: 'lines', mask: 'lines' }).lines; });
    const geo = { aveces: box($('#aveces')) };

    // ==============================================================
    // S1 · GANCHO
    // ==============================================================
    push('s1', 0, T.s2);
    reveal('#s1 .hook', 0.05, { d: 1.1, st: 0.1 });
    cue(0.05, 'hit', { v: 0.7 });
    {
      const p = $('#ul1 path');
      const a = geo.aveces, y = a.y + a.h * 0.93;
      p.setAttribute('d', `M${a.x + 4} ${y + 5} C ${a.x + a.w * 0.3} ${y + 12}, ${a.x + a.w * 0.72} ${y - 2}, ${a.x + a.w + 10} ${y + 3}`);
      const L = p.getTotalLength();
      tl.fromTo(p, { strokeDasharray: L, strokeDashoffset: L }, { strokeDashoffset: 0, duration: 0.55, ease: 'power2.inOut', immediateRender: true }, 1.3);
      tl.fromTo(p, { opacity: 0 }, { opacity: 1, duration: 0.01, immediateRender: true }, 1.3);
      cue(1.3, 'scribble', { d: 0.55 });
    }
    {
      const ON = [[-1, 1.55], [2.25, 2.9], [3.3, 99]];
      ON.forEach(([a, b]) => { if (a > 0) cue(a, 'bubble_on'); if (b < 4) cue(b, 'bubble_off'); });
      const bubble = $('#bubble'), dots = $$('#bubble i'), stT = $('#st-typing'), stO = $('#st-online');
      const back = ease('back.out(2.2)');
      procs.push(t => {
        if (t > T.s2 + 0.2) return;
        let on = false, last = -99;
        for (const [a, b] of ON) if (t >= a) { on = t < b; last = on ? a : b; }
        const since = t - last;
        let s, o;
        if (on) { s = 0.5 + 0.5 * back(clamp(since / 0.28)); o = clamp(since / 0.1); }
        else { const u = clamp(since / 0.16); s = 1 - 0.5 * u; o = 1 - u; }
        bubble.style.transform = `scale(${s})`;
        bubble.style.opacity = o;
        dots.forEach((d, i) => {
          const ph = ((t * 1.45 - i * 0.16) % 1 + 1) % 1;
          const bump = ph < 0.5 ? Math.sin(ph * 2 * Math.PI) : 0;
          d.style.transform = `translateY(${(-10 * bump).toFixed(2)}px)`;
          d.style.opacity = (0.32 + 0.6 * bump).toFixed(3);
        });
        const k = on ? clamp(since / 0.12) : 1 - clamp(since / 0.12);
        stT.style.opacity = k;
        stO.style.opacity = 1 - k;
      });
    }
    wipe('#s2', T.s2 - 0.55);
    drift('s1', T.s2 - 0.6);
    cue(T.s2 - 0.55, 'whoosh');
    hideAt('s1', T.s2 + 0.2);

    // ==============================================================
    // S2 · DEFINICIÓN
    // ==============================================================
    push('s2', T.s2 - 0.55, T.s3);
    kicker('#s2 .kicker', 4.05);
    reveal(lines('#s2 .term').slice(0, 1), 4.12, { d: 1.1 });
    cue(4.12, 'hit', { v: 0.5 });
    {
      const f = $('#flicker');
      const chars = [...f.textContent];
      f.innerHTML = chars.map(ch => `<span>${ch}</span>`).join('');
      const spans = $$('span', f);
      const rnd = mulberry32(1957);
      const sched = chars.map(() => {
        const on1 = 4.42 + rnd() * 0.78;
        const blips = [];
        let tt = on1 + 0.12 + rnd() * 0.2;
        while (tt < 5.45) {
          if (rnd() < 0.42) blips.push([tt, tt + 0.07 + rnd() * 0.07]);
          tt += 0.16 + rnd() * 0.26;
        }
        return { on1, blips };
      });
      sched.forEach(s => { cue(s.on1, 'flick'); s.blips.forEach(b => cue(b[1], 'flick', { v: 0.6 })); });
      procs.push(t => {
        spans.forEach((sp, i) => {
          const s = sched[i];
          const vis = t >= s.on1 && !s.blips.some(b => t >= b[0] && t < b[1]);
          sp.style.opacity = vis ? 1 : 0;
        });
      });
    }
    reveal('#s2 .phon', 5.35, { d: 0.9 });
    tl.fromTo('#s2 .hr', { scaleX: 0 }, { scaleX: 1, duration: 0.9, ease: 'power3.inOut', immediateRender: true }, 5.5);
    reveal([$('#sense1 .n > span'), ...$('#sense1 .txt')._lines], 5.75, { st: 0.09 });
    cue(5.75, 'tick', { v: 0.6 });
    reveal([$('#sense2 .n > span'), ...$('#sense2 .txt')._lines], 7.45, { st: 0.09 });
    cue(7.45, 'tick', { v: 0.6 });
    exitUp([...lines('#s2 .kicker'), ...lines('#s2 .term'), ...lines('#s2 .phon'), ...$('#sense1 .txt')._lines, ...$('#sense2 .txt')._lines, $('#sense1 .n > span'), $('#sense2 .n > span')], T.s3 - 0.62, { st: 0.02 });
    tl.to('#s2 .hr', { scaleX: 0, transformOrigin: '100% 50%', duration: 0.45, ease: 'power3.in' }, T.s3 - 0.55);
    cue(T.s3 - 0.6, 'whoosh', { v: 0.6 });
    tl.fromTo('#s3', { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.01, immediateRender: true }, T.s3 - 0.05);
    hideAt('s2', T.s3 + 0.1);

    // ==============================================================
    // S3 · LABORATORIO (registro acumulativo)
    // ==============================================================
    push('s3', T.s3, T.s4);
    reveal('#s3 .figlabel', 10.42, { d: 0.9 });
    reveal('#s3 .figsub', 10.52, { d: 0.9 });
    buildChart();
    reveal('#s3 .caption', 15.6, { d: 1.1, st: 0.1 });
    cue(15.6, 'hit', { v: 0.8 });
    // corte seco a negro
    tl.fromTo('#s4', { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.01, immediateRender: true }, T.s4);
    cue(T.s4, 'cut');
    hideAt('s3', T.s4 + 0.05);

    // ==============================================================
    // S4 · TRAGAMONEDAS
    // ==============================================================
    push('s4', T.s4, T.s5);
    kicker('#s4 .kicker', 18.5);
    buildSlots();
    reveal('#s4 .casi', 20.45, { d: 0.7 });
    reveal('#s4 .statement', 20.62, { d: 1.1, st: 0.1 });
    cue(20.62, 'hit', { v: 0.7 });
    reveal('#s4 .cite', 21.3, { d: 0.9 });
    wipe('#s5', T.s5 - 0.55);
    drift('s4', T.s5 - 0.6);
    cue(T.s5 - 0.55, 'whoosh');
    hideAt('s4', T.s5 + 0.2);

    // ==============================================================
    // S5 · VÍNCULOS SANOS
    // ==============================================================
    push('s5', T.s5 - 0.55, T.s6);
    reveal('#s5 .head', 24.5, { d: 1.1, st: 0.1 });
    cue(24.5, 'hit', { v: 0.6 });
    const G = buildGraphs();
    reveal('#s5 .caption', 29.4, { d: 1.1, st: 0.12 });
    cue(29.4, 'hit', { v: 0.6 });
    wipe('#s6', T.s6 - 0.55);
    cue(T.s6 - 0.55, 'whoosh', { v: 0.8 });
    hideAt('s5', T.s6 + 0.2);

    // ==============================================================
    // S6 · VÍNCULOS TÓXICOS Y VIOLENTOS
    // ==============================================================
    reveal('#s6 .head', 33.75, { d: 1.1, st: 0.1 });
    cue(33.75, 'hit', { v: 0.8, dark: 1 });
    G.toxic();
    exitUp('#s6 .head', 39.45, { st: 0.04 });
    tl.to('#g6', { autoAlpha: 0, y: -60, duration: 0.5, ease: 'power3.in' }, 39.5);
    tl.fromTo('#s6b', { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.01, immediateRender: true }, T.s6b - 0.05);
    hideAt('s6', T.s6b + 0.1);

    // ==============================================================
    // S6b · CICLO DE LA VIOLENCIA
    // ==============================================================
    push('s6b', T.s6b, T.s7);
    kicker('#s6b .kicker', 40.05);
    buildCycle();
    reveal('#s6b .final', 43.65, { d: 1.15, st: 0.12 });
    reveal('#s6b .cite', 44.4, { d: 0.9 });

    // ==============================================================
    // S7 · LA DIFERENCIA
    // ==============================================================
    wipe('#s7 .panel.top', T.s7 - 0.3, 'down', 0.66);
    wipe('#s7 .panel.bot', T.s7 - 0.3, 'up', 0.66);
    cue(T.s7 - 0.3, 'whoosh', { v: 1 });
    tl.fromTo('#s7 .seam', { scaleX: 0 }, { scaleX: 1, duration: 0.7, ease: 'power3.inOut', immediateRender: true }, T.s7 + 0.2);
    kicker('#s7 .top .tag', 47.55);
    reveal('#s7 .top .big', 47.65, { d: 1.1, st: 0.1 });
    cue(47.65, 'healthy_tone');
    kicker('#s7 .bot .tag', 49.15);
    reveal('#s7 .bot .big', 49.25, { d: 1.1, st: 0.1 });
    cue(49.25, 'violent_tone');
    hideAt('s6b', T.s7 + 0.4);

    // ==============================================================
    // S8 · CIERRE
    // ==============================================================
    wipe('#s8', T.s8 - 0.25, 'center', 0.66);
    cue(T.s8 - 0.25, 'whoosh', { v: 0.7 });
    push('s8', T.s8 - 0.25, T.end);
    reveal('#s8 .head', 54.8, { d: 1.15, st: 0.11 });
    cue(54.8, 'final_hit');
    tl.fromTo('#s8 .rule2', { scaleX: 0 }, { scaleX: 1, duration: 0.9, ease: 'power3.inOut', immediateRender: true }, 55.7);
    reveal($('#s8 .help')._lines, 55.85, { st: 0.08 });
    reveal('#s8 .line144', 56.45, { d: 1.0, st: 0.1 });
    cue(56.45, 'tick', { v: 0.8 });
    reveal($('#s8 .sources')._lines, 57.0, { st: 0.06 });
    hideAt('s7', T.s8 + 0.45);

    tl.set({}, {}, DUR);
    CUES.sort((a, b) => a.t - b.t);
    window.__cues = CUES;
    window.__T = T;
    window.__dur = DUR;
    window.__seek = t => { tl.seek(t, false); for (const p of procs) p(t); };
    window.__seek(0);
    window.__ready = true;
  }

  // ------------------------------------------------------------------
  // S3 · gráfico de registro acumulativo
  // ------------------------------------------------------------------
  function buildChart() {
    const S = $('#chart');
    const X0 = 70, X1 = 868, YB = 462, YT = 18, PW = X1 - X0, PH = YB - YT;
    const UE = 0.56;                       // momento en que se retira el premio
    const D0 = 11.05, D1 = 15.65;          // la pluma dibuja entre estos segundos
    const g = svg('g', {}, S);
    // papel milimetrado
    const grid = svg('g', {}, g);
    const step = PW / 20;
    for (let i = 0; i <= 20; i++) svg('line', { x1: X0 + i * step, y1: YT, x2: X0 + i * step, y2: YB, stroke: C.graphite, 'stroke-opacity': i % 5 ? 0.13 : 0.3, 'stroke-width': i % 5 ? 1 : 1.4 }, grid);
    for (let j = 0; YB - j * step >= YT - 0.5; j++) svg('line', { x1: X0, y1: YB - j * step, x2: X1, y2: YB - j * step, stroke: C.graphite, 'stroke-opacity': j % 5 ? 0.13 : 0.3, 'stroke-width': j % 5 ? 1 : 1.4 }, grid);
    fadeIn(grid, 10.5, 0.7);
    const axes = svg('path', { d: `M${X0} ${YT - 10} V${YB} H${X1 + 10}`, fill: 'none', stroke: C.ink, 'stroke-width': 3, 'stroke-linecap': 'square' }, g);
    const AL = (YB - YT + 10) + (PW + 10);
    tl.fromTo(axes, { strokeDasharray: AL, strokeDashoffset: AL }, { strokeDashoffset: 0, duration: 0.8, ease: 'power3.inOut', immediateRender: true }, 10.55);
    tl.fromTo(axes, { opacity: 0 }, { opacity: 1, duration: 0.01, immediateRender: true }, 10.55);
    const ylab = svg('text', { x: 0, y: 0, transform: `translate(${X0 - 22} ${YB}) rotate(-90)`, 'font-size': 22, fill: C.graphite, 'letter-spacing': '1.5' }, g);
    ylab.textContent = 'RESPUESTAS ACUMULADAS';
    const xlab = svg('text', { x: X1, y: YB + 42, 'text-anchor': 'end', 'font-size': 22, fill: C.graphite, 'letter-spacing': '1.5' }, g);
    xlab.textContent = 'TIEMPO →';
    fadeIn([ylab, xlab], 10.9, 0.6);

    // curvas: integración de una tasa de respuesta con ruido
    const N = 900, rnd = mulberry32(31);
    const pipsB = [0.035, 0.08, 0.17, 0.205, 0.235, 0.33, 0.405, 0.44, 0.515];
    const pipsA = []; for (let u = 0.04; u < UE - 0.01; u += 0.048) pipsA.push(+u.toFixed(3));
    function integrate(rate) {
      const ys = [0];
      for (let i = 1; i <= N; i++) ys.push(ys[i - 1] + rate((i - 0.5) / N) / N);
      return ys;
    }
    let nB = 0.6, nA = 0.6;
    const rawB = integrate(u => {
      nB += (rnd() - 0.5) * 0.35; nB = clamp(nB, 0.15, 1);
      if (u < UE) return 1.0 + 0.35 * (nB - 0.5);
      const k = Math.exp(-(u - UE) / 0.3);
      const pause = Math.sin((u - UE) * 70 + Math.sin((u - UE) * 23) * 2) < -0.35 + 0.9 * (1 - k) ? 0.08 : 1;
      return k * pause * (1.05 + 0.4 * (nB - 0.5));
    });
    const rawA = integrate(u => {
      nA += (rnd() - 0.5) * 0.3; nA = clamp(nA, 0.2, 1);
      if (u < UE) {
        const near = pipsA.some(p => u > p && u < p + 0.008);   // pausita tras cada premio
        return near ? 0.1 : 0.72 + 0.2 * (nA - 0.5);
      }
      const k = Math.exp(-(u - UE) / 0.045);
      return 0.95 * k + (u < UE + 0.25 && Math.sin(u * 120) > 0.92 ? 0.05 : 0);
    });
    const sB = 0.94 / rawB[N], sA = 0.46 / rawA[N];
    const ptB = rawB.map((y, i) => [X0 + (i / N) * PW, YB - y * sB * PH]);
    const ptA = rawA.map((y, i) => [X0 + (i / N) * PW, YB - y * sA * PH]);
    const at = (pts, u) => { const f = u * N, i = Math.min(N - 1, Math.floor(f)), r = f - i; return [lerp(pts[i][0], pts[i + 1][0], r), lerp(pts[i][1], pts[i + 1][1], r)]; };

    // marca de extinción
    const xE = X0 + UE * PW;
    const ext = svg('line', { x1: xE, y1: YB, x2: xE, y2: YT + 6, stroke: C.ink, 'stroke-width': 2.2, 'stroke-dasharray': '9 9', 'stroke-opacity': 0.75 }, g);
    const extLab = svg('text', { x: xE + 14, y: YB - 18, 'font-size': 21, fill: C.ink, 'letter-spacing': '0.5' }, g);
    extLab.textContent = '← se retira el premio';
    const tE = D0 + UE * (D1 - D0);
    tl.fromTo(ext, { attr: { y2: YB } }, { attr: { y2: YT + 6 }, duration: 0.45, ease: 'power3.out', immediateRender: true }, tE);
    fadeIn(extLab, tE + 0.1, 0.4, { x: -10 });
    cue(tE, 'extinction');

    // leyenda
    const leg = svg('g', {}, g);
    svg('line', { x1: X0 + 22, y1: YT + 26, x2: X0 + 62, y2: YT + 26, stroke: C.red, 'stroke-width': 5, 'stroke-linecap': 'round' }, leg);
    svg('text', { x: X0 + 76, y: YT + 33, 'font-size': 21, fill: C.redInk, 'font-weight': 600 }, leg).textContent = 'premio a veces (al azar)';
    svg('line', { x1: X0 + 22, y1: YT + 62, x2: X0 + 62, y2: YT + 62, stroke: C.ink, 'stroke-width': 4, 'stroke-linecap': 'round' }, leg);
    svg('text', { x: X0 + 76, y: YT + 69, 'font-size': 21, fill: C.ink, 'font-weight': 600 }, leg).textContent = 'premio siempre';
    fadeIn(leg, 10.95, 0.5, { y: 8 });

    // trazos dinámicos
    const pathA = svg('path', { fill: 'none', stroke: C.ink, 'stroke-width': 4, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }, g);
    const pathB = svg('path', { fill: 'none', stroke: C.red, 'stroke-width': 5, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }, g);
    const pipG = svg('g', {}, g);
    const mkPip = (pts, u, col) => {
      const [x, y] = at(pts, u);
      return svg('line', { x1: x - 1, y1: y - 1, x2: x + 9, y2: y + 13, stroke: col, 'stroke-width': 3, 'stroke-linecap': 'round', opacity: 0 }, pipG);
    };
    const pA = pipsA.map(u => ({ u, e: mkPip(ptA, u, C.ink) }));
    const pB = pipsB.map(u => ({ u, e: mkPip(ptB, u, C.redInk) }));
    pA.forEach(p => cue(D0 + p.u * (D1 - D0), 'pipA'));
    pB.forEach(p => cue(D0 + p.u * (D1 - D0), 'pipB'));
    cue(D0, 'pen', { d: D1 - D0 });
    const headA = svg('circle', { r: 7.5, fill: C.ink, opacity: 0 }, g);
    const headB = svg('circle', { r: 8.5, fill: C.red, opacity: 0 }, g);
    const endB = at(ptB, 1), endA = at(ptA, 1);
    const annB = svg('text', { x: X1, y: endB[1] - 24, 'text-anchor': 'end', 'font-size': 22, fill: C.redInk, 'font-weight': 600 }, g);
    annB.textContent = 'sigue insistiendo';
    const annA = svg('text', { x: X1, y: endA[1] + 42, 'text-anchor': 'end', 'font-size': 22, fill: C.ink, 'font-weight': 600 }, g);
    annA.textContent = 'se apaga rápido';
    fadeIn(annB, 15.2, 0.5, { y: 8 });
    fadeIn(annA, 14.6, 0.5, { y: -8 });

    procs.push(t => {
      if (t < T.s3 - 0.1 || t > T.s4 + 0.1) return;
      const u = prog(t, D0, D1 - D0);
      const k = Math.floor(u * N);
      const cut = (pts) => { const a = pts.slice(0, k + 1); if (u > 0) a.push(at(pts, u)); return a; };
      pathA.setAttribute('d', u > 0 ? pathFrom(cut(ptA)) : '');
      pathB.setAttribute('d', u > 0 ? pathFrom(cut(ptB)) : '');
      const hA = at(ptA, u), hB = at(ptB, u);
      const vis = u > 0 && u < 1 ? 1 : (u >= 1 ? Math.max(0, 1 - (t - D1) / 0.4) : 0);
      headA.setAttribute('cx', hA[0]); headA.setAttribute('cy', hA[1]); headA.setAttribute('opacity', vis);
      headB.setAttribute('cx', hB[0]); headB.setAttribute('cy', hB[1]); headB.setAttribute('opacity', vis);
      for (const p of [...pA, ...pB]) p.e.setAttribute('opacity', u >= p.u ? 1 : 0);
    });
  }

  // ------------------------------------------------------------------
  // S4 · tragamonedas
  // ------------------------------------------------------------------
  function symbolSVG(kind) {
    switch (kind) {
      case 'heart':
        return `<svg width="150" height="150" viewBox="-75 -75 150 150"><path d="M0 52 C -10 40, -64 10, -64 -22 C -64 -48, -38 -62, -18 -54 C -8 -50, -2 -42, 0 -36 C 2 -42, 8 -50, 18 -54 C 38 -62, 64 -48, 64 -22 C 64 10, 10 40, 0 52 Z" fill="${C.red}"/></svg>`;
      case 'cross':
        return `<svg width="150" height="150" viewBox="-75 -75 150 150"><path d="M-44 -44 L44 44 M44 -44 L-44 44" stroke="${C.bone}" stroke-width="15" stroke-linecap="round"/></svg>`;
      case 'dots':
        return `<svg width="150" height="150" viewBox="-75 -75 150 150"><circle cx="-42" cy="0" r="14" fill="${C.bone}"/><circle cx="0" cy="0" r="14" fill="${C.bone}"/><circle cx="42" cy="0" r="14" fill="${C.bone}"/></svg>`;
      default:
        return `<svg width="150" height="150" viewBox="-75 -75 150 150"><text x="0" y="52" text-anchor="middle" font-family="Instrument Serif" font-size="170" fill="${C.bone}">?</text></svg>`;
    }
  }
  function buildSlots() {
    const ORDERS = [
      ['heart', 'cross', 'dots', 'q', 'heart', 'dots', 'cross', 'q'],
      ['dots', 'heart', 'q', 'cross', 'heart', 'q', 'dots', 'cross'],
      ['cross', 'q', 'heart', 'dots', 'cross', 'heart', 'q', 'dots'],
    ];
    const FINAL = ['heart', 'heart', 'cross'];
    const SH = 290, TS = 18.6, STOPS = [19.35, 19.74, 20.32];
    const slots = $$('#s4 .slot');
    const defs = svg('svg', { width: 0, height: 0, style: 'position:absolute' }, $('#s4 .cam'));
    const filters = slots.map((_, i) => {
      const f = svg('filter', { id: 'vb' + i, x: '-10%', y: '-30%', width: '120%', height: '160%' }, defs);
      return svg('feGaussianBlur', { stdDeviation: '0 0' }, f);
    });
    fadeIn(slots, 18.45, 0.5, { y: 30 });
    const reels = slots.map((slot, i) => {
      const strip = $('.strip', slot);
      const order = ORDERS[i];
      strip.innerHTML = [...order, ...order].map(k => `<div class="sym">${symbolSVG(k)}</div>`).join('');
      strip.style.filter = `url(#vb${i})`;
      const n = order.length;
      const target = order.indexOf(FINAL[i]);
      const start = (i * 3 + 1) % n;
      // perfil de velocidad: arranque, crucero, frenada corta y rebote
      const te = STOPS[i], dt = 1 / 600;
      const vprof = t => (t < TS ? 0 : t < te - 0.3 ? smooth(clamp((t - TS) / 0.28)) : 1 - 0.8 * smooth(clamp((t - (te - 0.3)) / 0.3)));
      let unit = 0;
      for (let t = TS; t < te; t += dt) unit += vprof(t + dt / 2) * dt;
      let laps = 0, dist;
      do { dist = ((target - start + n) % n) + laps * n; laps++; } while (dist / unit < 13.5);
      const V = dist / unit;
      const table = [];
      let acc = 0;
      for (let t = TS; t <= te + 1e-9; t += dt) { table.push(acc); acc += vprof(t + dt / 2) * V * dt; }
      const pos = t => {
        if (t <= TS) return start;
        if (t >= te) {
          const tau = t - te, v0 = 0.2 * V, w = 2 * Math.PI * 5.2;
          return start + dist + (v0 / w) * Math.sin(w * tau) * Math.exp(-tau * 9);
        }
        return start + table[Math.min(table.length - 1, Math.round((t - TS) / dt))];
      };
      const vel = t => (t <= TS || t >= te ? 0 : vprof(t) * V);
      cue(te, 'slot_stop', { i, sym: FINAL[i] });
      return { strip, n, pos, vel, blur: filters[i] };
    });
    cue(TS, 'slot_spin', { d: STOPS[2] - TS });
    cue(STOPS[2] + 0.02, 'nearmiss');
    procs.push(t => {
      if (t < T.s4 - 0.1 || t > T.s5 + 0.1) return;
      for (const r of reels) {
        const p = r.pos(t);
        const m = ((p % r.n) + r.n) % r.n;
        r.strip.style.transform = `translateY(${(-m * SH).toFixed(2)}px)`;
        r.blur.setAttribute('stdDeviation', `0 ${Math.min(16, r.vel(t) * 1.15).toFixed(2)}`);
      }
    });
  }

  // ------------------------------------------------------------------
  // S5 / S6 · la base estable y la base que va y viene
  // ------------------------------------------------------------------
  function buildGraphs() {
    const BY = 330, GW = 888;
    const wave = x => BY - (118 + 38 * Math.sin(2 * Math.PI * x / 360 + 0.4) + 15 * Math.sin(2 * Math.PI * x / 170 + 2.0));
    const wavePts = []; for (let x = 0; x <= GW; x += 3) wavePts.push([x, wave(x)]);
    const waveD = pathFrom(wavePts);
    const labels = (parent, col, strong) => {
      const a = svg('text', { x: 0, y: 112 - 52, 'font-size': 24, fill: col, 'letter-spacing': '1.2' }, parent);
      a.innerHTML = `<tspan font-weight="600">LO QUE VARÍA</tspan><tspan fill-opacity="0.8"> — deseo · tiempo · sorpresas</tspan>`;
      const b = svg('text', { x: 0, y: BY + 60, 'font-size': 24, fill: strong, 'letter-spacing': '1.2' }, parent);
      b.innerHTML = `<tspan font-weight="600">LA BASE</tspan><tspan fill-opacity="0.8"> — respeto · cuidado · seguridad</tspan>`;
      return [a, b];
    };

    // ---- S5 (hueso) ----
    const g5 = $('#g5');
    const base5 = svg('path', { d: `M6 ${BY} H${GW - 6}`, fill: 'none', stroke: C.ink, 'stroke-width': 13, 'stroke-linecap': 'round' }, g5);
    const wave5 = svg('path', { d: waveD, fill: 'none', stroke: C.graphite, 'stroke-width': 4.5, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, g5);
    const pen5 = svg('circle', { r: 8, fill: C.graphite, opacity: 0 }, g5);
    const [lw5, lb5] = labels(g5, C.graphite, C.ink);
    const BL = GW - 12;
    tl.fromTo(base5, { strokeDasharray: BL, strokeDashoffset: BL }, { strokeDashoffset: 0, duration: 1.2, ease: 'power3.inOut', immediateRender: true }, 25.55);
    tl.fromTo(base5, { opacity: 0 }, { opacity: 1, duration: 0.01, immediateRender: true }, 25.55);
    cue(25.55, 'base_line', { d: 1.2 });
    fadeIn(lb5, 26.3, 0.6, { y: 10 });
    const WL = wave5.getTotalLength();
    const W0 = 26.75, W1 = 28.95;
    tl.fromTo(wave5, { strokeDasharray: WL, strokeDashoffset: WL }, { strokeDashoffset: 0, duration: W1 - W0, ease: 'sine.inOut', immediateRender: true }, W0);
    tl.fromTo(wave5, { opacity: 0 }, { opacity: 1, duration: 0.01, immediateRender: true }, W0);
    cue(W0, 'wave', { d: W1 - W0 });
    fadeIn(lw5, 27.15, 0.6, { y: -10 });
    const sineIO = ease('sine.inOut');
    procs.push(t => {
      if (t < T.s5 || t > T.s6 + 0.2) return;
      const u = sineIO(prog(t, W0, W1 - W0));
      const P = wave5.getPointAtLength(u * WL);
      pen5.setAttribute('cx', P.x); pen5.setAttribute('cy', P.y);
      pen5.setAttribute('opacity', u > 0 && u < 1 ? 1 : (u >= 1 ? Math.max(0, 1 - (t - W1) / 0.4) : 0));
    });

    // ---- S6 (borravino): arranca igual y la base se rompe ----
    const g6 = $('#g6');
    const ref = svg('path', { d: `M0 ${BY} H${GW}`, stroke: C.bone, 'stroke-opacity': 0.42, 'stroke-width': 2.5, 'stroke-dasharray': '10 10', fill: 'none' }, g6);
    const refLab = svg('text', { x: GW, y: BY + 40, 'text-anchor': 'end', 'font-size': 23, fill: C.bone, 'fill-opacity': 0.66, 'letter-spacing': '1.2' }, g6);
    refLab.textContent = 'LA BASE';
    const wave6 = svg('path', { d: waveD, fill: 'none', stroke: C.bone, 'stroke-opacity': 0.55, 'stroke-width': 4.5, 'stroke-linecap': 'round' }, g6);
    const [lw6, lb6] = labels(g6, C.bone, C.bone);
    const line6 = svg('path', { fill: 'none', stroke: C.bone, 'stroke-width': 11, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, g6);
    const pen6 = svg('circle', { r: 11, fill: C.red, opacity: 0 }, g6);
    // picos y caídas: suben despacio (la reconciliación) y caen de golpe (el castigo)
    const EX = [
      [0, 0], [128, -182, 'cariño', 'peak'], [205, 138, 'frialdad', 'valley'], [352, -150, 'atención', 'peak'],
      [432, 152, 'silencio', 'valley'], [600, -190, 'promesas', 'peak'], [684, 170, 'desprecio', 'valley'], [830, -96], [GW, -40],
    ];
    const jit = mulberry32(7);
    const jitter = []; for (let x = 0; x <= GW + 8; x += 4) jitter.push((jit() - 0.5) * 6);
    const disp = x => {
      let i = 0; while (i < EX.length - 2 && x > EX[i + 1][0]) i++;
      const [xa, ya] = EX[i], [xb, yb] = EX[i + 1];
      const u = clamp((x - xa) / (xb - xa));
      const s = yb > ya ? 1 - Math.pow(1 - u, 2.6) : 0.5 - 0.5 * Math.cos(Math.PI * u);
      const v = lerp(ya, yb, s);
      return v + jitter[Math.round(x / 4)] * Math.min(1, Math.abs(v) / 50);
    };
    const P0 = 34.35, P1 = 38.95;
    const exLabels = EX.filter(e => e[2]).map(([x, dy, word, kind]) => {
      const y = BY + dy + (kind === 'peak' ? -30 : 70);
      const tx = svg('text', { x, y, 'text-anchor': 'middle', style: 'font-family: "Instrument Serif"; font-style: italic', 'font-size': 62, fill: kind === 'peak' ? C.bone : '#F0574A', opacity: 0 }, g6);
      tx.textContent = word;
      const t = P0 + (x / GW) * (P1 - P0);
      cue(t, kind, { word });
      return { tx, t, kind };
    });
    tl.to([wave6, lw6, lb6], { autoAlpha: 0, duration: 0.45, ease: 'power2.in' }, 33.9);
    tl.fromTo([ref, refLab], { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.5, immediateRender: true }, 34.3);
    cue(P0, 'toxic_line', { d: P1 - P0 });
    const outQ = ease('power3.out');
    function toxic() {
      procs.push(t => {
        if (t < T.s6 - 0.7 || t > T.s6b + 0.2) return;
        const u = prog(t, P0, P1 - P0);
        const px = u * GW;
        const pts = [];
        for (let x = 0; x <= GW; x += 4) {
          const s = clamp((px - x) / 70);
          pts.push([x, BY + disp(x) * smooth(s)]);
        }
        line6.setAttribute('d', pathFrom(pts));
        const head = [px, BY + 0];
        pen6.setAttribute('cx', head[0]); pen6.setAttribute('cy', head[1]);
        pen6.setAttribute('opacity', u > 0 && u < 1 ? 1 : 0);
        for (const L of exLabels) {
          const k = outQ(prog(t, L.t + 0.08, 0.4));
          L.tx.setAttribute('opacity', k);
          L.tx.setAttribute('transform', `translate(0 ${((1 - k) * (L.kind === 'peak' ? 14 : -14)).toFixed(2)})`);
        }
      });
    }
    return { toxic };
  }

  // ------------------------------------------------------------------
  // S6b · ciclo de la violencia (Walker, 1979)
  // ------------------------------------------------------------------
  function buildCycle() {
    const S = $('#cycle');
    const cx = 548, cy = 790, r = 216;
    const pt = a => [cx + r * Math.cos(a * Math.PI / 180), cy + r * Math.sin(a * Math.PI / 180)];
    svg('circle', { cx, cy, r, fill: 'none', stroke: C.bone, 'stroke-opacity': 0.16, 'stroke-width': 3 }, S);
    const arc = svg('path', { fill: 'none', stroke: C.bone, 'stroke-width': 5, 'stroke-linecap': 'round' }, S);
    const nodes = [
      { a: -90, name: 'tensión', lx: 0, ly: -46, anchor: 'middle' },
      { a: 30, name: 'explosión', lx: 24, ly: 78, anchor: 'start' },
      { a: 150, name: 'luna de miel', lx: -24, ly: 78, anchor: 'end' },
    ];
    // flechas en sentido horario a mitad de cada tramo
    const arrows = [-30, 90, 210].map(a => {
      const [x, y] = pt(a);
      const g = svg('g', { transform: `translate(${x} ${y}) rotate(${a + 90})`, opacity: 0 }, S);
      svg('path', { d: 'M-12 -14 L4 0 L-12 14', fill: 'none', stroke: C.bone, 'stroke-width': 5, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, g);
      return { a, g };
    });
    nodes.forEach(n => {
      const [x, y] = pt(n.a);
      n.dot = svg('circle', { cx: x, cy: y, r: 12, fill: C.bone }, S);
      n.ring = svg('circle', { cx: x, cy: y, r: 12, fill: 'none', stroke: C.red, 'stroke-width': 3, opacity: 0 }, S);
      n.lab = svg('text', { x: x + n.lx, y: y + n.ly, 'text-anchor': n.anchor, class: 'lab', opacity: 0 }, S);
      n.lab.textContent = n.name;
    });
    const tag = svg('text', { x: pt(150)[0] - 26, y: pt(150)[1] + 124, 'text-anchor': 'end', style: 'font-family: "IBM Plex Mono"', 'font-size': 25, 'font-weight': 600, 'letter-spacing': '1.5', fill: '#F0574A', opacity: 0 }, S);
    tag.textContent = '(EL PREMIO)';
    const center = svg('text', { x: cx, y: cy + 18, 'text-anchor': 'middle', style: 'font-family: "Instrument Serif"; font-style: italic', 'font-size': 60, fill: C.bone, 'fill-opacity': 0.8, opacity: 0 }, S);
    center.textContent = 'y se repite';
    const dot = svg('circle', { r: 15, fill: C.red, opacity: 0 }, S);

    // recorrido: vuelta 1 lenta, vuelta 2 más rápida, se queda en "luna de miel"
    const K = [[40.35, -90], [42.55, 270], [43.35, 510]];
    const angle = t => {
      if (t <= K[0][0]) return K[0][1];
      for (let i = 0; i < K.length - 1; i++) {
        const [ta, aa] = K[i], [tb, ab] = K[i + 1];
        if (t <= tb) return lerp(aa, ab, i === 0 ? ease('sine.in')(prog(t, ta, tb - ta)) * 0.25 + 0.75 * prog(t, ta, tb - ta) : ease('power1.out')(prog(t, ta, tb - ta)));
      }
      return K[K.length - 1][1];
    };
    // instantes en que el punto pasa por cada nodo
    const hits = [];
    for (let t = 40.3; t <= 43.4; t += 1 / 600) {
      const a0 = angle(t), a1 = angle(t + 1 / 600);
      for (const [i, n] of nodes.entries()) {
        for (let k = -1; k <= 2; k++) {
          const target = n.a + 360 * k;
          if (a0 < target && a1 >= target) hits.push({ t: t + 1 / 600, i });
        }
      }
    }
    hits.unshift({ t: 40.35, i: 0 });
    hits.forEach(h => cue(h.t, ['tension', 'explosion', 'honeymoon'][h.i]));
    tl.fromTo(dot, { attr: { r: 0 } }, { attr: { r: 15 }, duration: 0.35, ease: 'back.out(2)', immediateRender: true }, 40.2);
    tl.set(dot, { opacity: 1 }, 40.2);
    fadeIn(center, 42.7, 0.6, { y: 10 });
    fadeIn(tag, 41.95, 0.5, { y: -8 });
    const outQ = ease('power3.out');
    procs.push(t => {
      if (t < T.s6b - 0.1 || t > T.s7 + 0.6) return;
      const a = angle(t);
      const [x, y] = pt(a);
      dot.setAttribute('cx', x); dot.setAttribute('cy', y);
      const sweep = clamp(a + 90, 0, 360);
      if (sweep >= 359.9) arc.setAttribute('d', `M${cx} ${cy - r} A${r} ${r} 0 1 1 ${cx - 0.01} ${cy - r}`);
      else if (sweep > 0.2) {
        const [ex, ey] = pt(-90 + sweep);
        arc.setAttribute('d', `M${cx} ${cy - r} A${r} ${r} 0 ${sweep > 180 ? 1 : 0} 1 ${ex} ${ey}`);
      } else arc.setAttribute('d', '');
      arrows.forEach(ar => ar.g.setAttribute('opacity', a >= ar.a + 8 ? 1 : 0));
      nodes.forEach((n, i) => {
        const mine = hits.filter(h => h.i === i && h.t <= t);
        const first = mine.length ? mine[0].t : null;
        const k = first == null ? 0 : outQ(prog(t, first, 0.45));
        n.lab.setAttribute('opacity', k);
        n.lab.setAttribute('transform', `translate(0 ${((1 - k) * 12).toFixed(2)})`);
        const last = mine.length ? mine[mine.length - 1].t : null;
        const pulse = last == null ? 0 : Math.exp(-(t - last) * 3.2);
        const [nx, ny] = pt(n.a);
        n.dot.setAttribute('r', (12 + 7 * pulse).toFixed(2));
        n.dot.setAttribute('fill', pulse > 0.25 ? C.red : C.bone);
        const rp = last == null ? 1 : prog(t, last, 0.8);
        n.ring.setAttribute('r', (14 + 46 * outQ(rp)).toFixed(2));
        n.ring.setAttribute('opacity', last == null ? 0 : (1 - rp) * 0.9);
        n.ring.setAttribute('cx', nx); n.ring.setAttribute('cy', ny);
      });
    });
  }

  const fontsToLoad = [
    '400 100px "Instrument Serif"', 'italic 400 100px "Instrument Serif"', '400 50px "Instrument Sans"', 'italic 400 50px "Instrument Sans"',
    '500 50px "Instrument Sans"', '600 50px "Instrument Sans"', '400 30px "IBM Plex Mono"', '500 30px "IBM Plex Mono"', '600 30px "IBM Plex Mono"',
    'italic 400 30px "IBM Plex Mono"',
  ];
  Promise.all(fontsToLoad.map(f => document.fonts.load(f))).then(() => document.fonts.ready).then(build);
})();
