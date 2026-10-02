/* Render del reel con Chromium (Playwright).
   node render.cjs still <t> <out.png>
   node render.cjs sheet <t1,t2,...> <out.png>        (hoja de contactos, 4 columnas)
   node render.cjs cues <out.json>
   node render.cjs cover <out.png>
   node render.cjs video <out.mp4> [jobs]              (sin audio; el audio se mezcla aparte) */
const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const { chromium } = require('playwright');

const ROOT = __dirname;
const FPS = 30;
const MIME = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.ttf': 'font/ttf', '.png': 'image/png', '.json': 'application/json' };

function serve() {
  return new Promise(res => {
    const srv = http.createServer((req, rsp) => {
      const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
      fs.readFile(p, (err, data) => {
        if (err) { rsp.writeHead(404); rsp.end(); return; }
        rsp.writeHead(200, { 'Content-Type': MIME[path.extname(p)] || 'application/octet-stream' });
        rsp.end(data);
      });
    }).listen(0, '127.0.0.1', () => res(srv));
  });
}

async function openPage(port, page0 = 'index.html') {
  const browser = await chromium.launch({ args: ['--force-color-profile=srgb', '--font-render-hinting=none', '--disable-lcd-text'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('PAGE ERROR', e));
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.error('console:', m.text()); });
  await page.goto(`http://127.0.0.1:${port}/${page0}`);
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 30000 });
  return { browser, page };
}

async function shot(page, t) {
  await page.evaluate(tt => window.__seek(tt), t);
  return page.screenshot({ type: 'png', clip: { x: 0, y: 0, width: 1080, height: 1920 } });
}

function ffmpeg(args, opts = {}) {
  const p = spawn('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', ...args], { stdio: ['pipe', 'inherit', 'inherit'], ...opts });
  return p;
}
const done = p => new Promise((res, rej) => p.on('close', c => (c === 0 ? res() : rej(new Error('ffmpeg ' + c)))));

async function renderRange(port, a, b, out) {
  const { browser, page } = await openPage(port);
  const enc = ffmpeg(['-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '8', '-pix_fmt', 'yuv444p', out]);
  const t0 = Date.now();
  for (let i = a; i < b; i++) {
    const buf = await shot(page, i / FPS);
    if (!enc.stdin.write(buf)) await new Promise(r => enc.stdin.once('drain', r));
    if ((i - a) % 60 === 0) console.log(`[${a}-${b}] frame ${i} (${((Date.now() - t0) / 1000).toFixed(0)} s)`);
  }
  enc.stdin.end();
  await done(enc);
  await browser.close();
}

(async () => {
  const [mode, a1, a2, a3] = process.argv.slice(2);
  const srv = await serve();
  const port = srv.address().port;
  try {
    if (mode === 'cover') {
      const { browser, page } = await openPage(port, 'cover.html');
      fs.writeFileSync(a1, await shot(page, 0));
      await browser.close();
    } else if (mode === 'still') {
      const { browser, page } = await openPage(port);
      fs.writeFileSync(a2, await shot(page, parseFloat(a1)));
      await browser.close();
    } else if (mode === 'sheet') {
      const ts = a1.split(',').map(Number);
      const { browser, page } = await openPage(port);
      const tmp = fs.mkdtempSync(path.join(require('os').tmpdir(), 'sheet'));
      const files = [];
      for (const [k, t] of ts.entries()) {
        const f = path.join(tmp, `f${k}.png`);
        fs.writeFileSync(f, await shot(page, t));
        files.push(f);
      }
      await browser.close();
      const cols = Math.min(4, files.length), rows = Math.ceil(files.length / cols);
      const inputs = files.flatMap(f => ['-i', f]);
      const scaled = files.map((_, k) => `[${k}:v]scale=540:960,drawtext=text='${ts[k].toFixed(2)}':x=12:y=12:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.6[v${k}]`).join(';');
      const layout = files.map((_, k) => `${(k % cols) * 540}_${Math.floor(k / cols) * 960}`).join('|');
      const pads = files.length < cols * rows ? '' : '';
      await done(ffmpeg([...inputs, '-filter_complex', `${scaled};${files.map((_, k) => `[v${k}]`).join('')}xstack=inputs=${files.length}:layout=${layout}:fill=gray[o]`, '-map', '[o]', '-frames:v', '1', a2]));
      fs.rmSync(tmp, { recursive: true });
      void pads;
    } else if (mode === 'cues') {
      const { browser, page } = await openPage(port);
      const cues = await page.evaluate(() => ({ T: window.__T, dur: window.__dur, cues: window.__cues }));
      fs.writeFileSync(a1, JSON.stringify(cues, null, 1));
      await browser.close();
    } else if (mode === 'video') {
      const jobs = parseInt(a2 || '4', 10);
      const total = Math.round(60 * FPS);
      const segDir = fs.mkdtempSync(path.join(process.env.SEG_DIR || require('os').tmpdir(), 'segs'));
      const per = Math.ceil(total / jobs);
      const segs = [];
      const work = [];
      for (let j = 0; j < jobs; j++) {
        const a = j * per, b = Math.min(total, (j + 1) * per);
        if (a >= b) break;
        const f = path.join(segDir, `seg${j}.mkv`);
        segs.push(f);
        work.push(renderRange(port, a, b, f));
      }
      await Promise.all(work);
      const list = path.join(segDir, 'list.txt');
      fs.writeFileSync(list, segs.map(s => `file '${s}'`).join('\n'));
      await done(ffmpeg(['-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', a1]));
      console.log('ok', a1, 'segmentos en', segDir);
    }
  } finally {
    srv.close();
  }
})().catch(e => { console.error(e); process.exit(1); });
