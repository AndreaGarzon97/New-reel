// Renderiza src/index.html cuadro a cuadro con Chromium (Playwright) y arma los MP4.
//
//   node tools/render.mjs                      → cuadros + video (con build/audio.wav si existe)
//   node tools/render.mjs --preview 0.5,7,26   → PNG sueltos en build/preview/
//   node tools/render.mjs --cues               → build/cues.json (marcas de sonido para audio.py)
//   node tools/render.mjs --range 600-720      → re-renderiza solo esos cuadros y re-encodea
//   node tools/render.mjs --encode-only        → solo encodea con los cuadros ya hechos
//   node tools/render.mjs --cover              → portada (src/portada.html) en dist/portada.png
//
// Variables: FFMPEG (ruta a ffmpeg), WORKERS (por defecto 4).
import { createRequire } from 'node:module';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); } catch { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SRC = path.join(ROOT, 'src');
const BUILD = path.join(ROOT, 'build');
const DIST = path.join(ROOT, 'dist');
const FPS = 30, DUR = 60, W = 1080, H = 1920;
const FFMPEG = process.env.FFMPEG || 'ffmpeg';
const WORKERS = +(process.env.WORKERS || 4);
const NAME = 'evitacion';

const args = process.argv.slice(2);
const flag = n => args.includes(n);
const opt = n => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : null; };

const MIME = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.png': 'image/png', '.woff2': 'font/woff2' };
function serve() {
  const server = http.createServer((req, res) => {
    const p = path.join(SRC, decodeURIComponent(new URL(req.url, 'http://x').pathname));
    if (!p.startsWith(SRC) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(p)] || 'application/octet-stream' });
    fs.createReadStream(p).pipe(res);
  });
  return new Promise(r => server.listen(0, '127.0.0.1', () => r(server)));
}

async function openPage(browser, url) {
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('error en la página:', e.message));
  await page.goto(url);
  await page.evaluate(() => window.__ready);
  // PNG sin pérdida vía CDP: bastante más rápido que page.screenshot()
  const cdp = await page.context().newCDPSession(page);
  page.shoot = async file => {
    const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', optimizeForSpeed: true });
    fs.writeFileSync(file, Buffer.from(data, 'base64'));
  };
  return page;
}

function ff(argv) {
  const r = spawnSync(FFMPEG, ['-hide_banner', '-loglevel', 'error', '-y', ...argv], { stdio: 'inherit' });
  if (r.status !== 0) throw new Error('ffmpeg falló: ' + argv.join(' '));
}

function encode(frames) {
  fs.mkdirSync(DIST, { recursive: true });
  const audio = path.join(BUILD, 'audio.wav');
  const video = ['-framerate', String(FPS), '-i', path.join(frames, '%05d.png')];
  // BT.709 explícito: si no, ffmpeg convierte con BT.601 y los colores se corren en el celular
  const venc = ['-vf', 'scale=out_color_matrix=bt709:out_range=tv:flags=lanczos+accurate_rnd+full_chroma_int',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-profile:v', 'high', '-pix_fmt', 'yuv420p',
    '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-movflags', '+faststart'];
  const main = path.join(DIST, `${NAME}_reel.mp4`);
  const silent = path.join(DIST, `${NAME}_reel_sin-audio.mp4`);
  if (fs.existsSync(audio)) {
    ff([...video, '-i', audio, ...venc, '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-t', String(DUR), main]);
    ff(['-i', main, '-an', '-c:v', 'copy', '-movflags', '+faststart', silent]);
    console.log(main);
  } else {
    console.warn('No hay build/audio.wav: corré primero tools/audio.py');
    ff([...video, ...venc, '-an', silent]);
  }
  console.log(silent);
}

async function main() {
  if (flag('--encode-only')) return encode(path.join(BUILD, 'frames'));
  const server = await serve();
  const url = `http://127.0.0.1:${server.address().port}/index.html`;
  const browser = await chromium.launch({ args: ['--force-color-profile=srgb', '--font-render-hinting=none'] });
  try {
    fs.mkdirSync(BUILD, { recursive: true });
    if (flag('--cues')) {
      const page = await openPage(browser, url);
      const c = await page.evaluate(() => window.__cues());
      fs.writeFileSync(path.join(BUILD, 'cues.json'), JSON.stringify(c));
      console.log(path.join(BUILD, 'cues.json'), c.cues.length, 'marcas');
      return;
    }
    if (flag('--cover')) {
      fs.mkdirSync(DIST, { recursive: true });
      const page = await openPage(browser, url.replace('index.html', 'portada.html'));
      await page.shoot(path.join(DIST, 'portada.png'));
      console.log(path.join(DIST, 'portada.png'));
      return;
    }
    if (flag('--preview')) {
      const dir = path.join(BUILD, 'preview');
      fs.mkdirSync(dir, { recursive: true });
      const page = await openPage(browser, url);
      for (const t of opt('--preview').split(',').map(Number)) {
        await page.evaluate(tt => window.__render(tt), t);
        const f = path.join(dir, `t${t.toFixed(2).padStart(6, '0')}.png`);
        await page.shoot(f);
        console.log(f);
      }
      return;
    }
    const frames = path.join(BUILD, 'frames');
    const total = FPS * DUR;
    const [a, b] = opt('--range') ? opt('--range').split('-').map(Number) : [0, total - 1];
    if (!opt('--range')) fs.rmSync(frames, { recursive: true, force: true });
    fs.mkdirSync(frames, { recursive: true });
    const count = b - a + 1, per = Math.ceil(count / WORKERS);
    let done = 0;
    const t0 = Date.now();
    await Promise.all([...Array(WORKERS)].map(async (_, w) => {
      const page = await openPage(browser, url);
      for (let i = a + w * per; i < Math.min(b + 1, a + (w + 1) * per); i++) {
        await page.evaluate(tt => window.__render(tt), i / FPS);
        await page.shoot(path.join(frames, `${String(i).padStart(5, '0')}.png`));
        if (++done % 150 === 0) {
          const el = (Date.now() - t0) / 1000;
          console.log(`${done}/${count} cuadros · ${el.toFixed(0)} s · faltan ~${(el / done * (count - done)).toFixed(0)} s`);
        }
      }
      await page.close();
    }));
    encode(frames);
  } finally {
    await browser.close();
    server.close();
  }
}

main().catch(e => { console.error(e); process.exit(1); });
