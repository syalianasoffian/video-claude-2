// Renders src/index.html frame-by-frame in headless Chromium and encodes with ffmpeg.
// usage: node src/render.js [--stills 1,5.5,9] [--guides] [--from s --to s] [--out file.mp4]
const http = require('http'), fs = require('fs'), path = require('path'), { spawn } = require('child_process');
const { chromium } = require('playwright');
const ROOT = path.resolve(__dirname, '..');
const args = process.argv.slice(2), opt = k => { const i = args.indexOf(k); return i < 0 ? null : args[i + 1]; };
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.woff2': 'font/woff2' };

const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(ROOT) || !fs.existsSync(p)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(res);
});

(async () => {
  await new Promise(r => server.listen(8765, r));
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 868 } });
  page.on('console', m => console.log('[page]', m.text())); page.on('pageerror', e => console.log('[err]', e.message));
  await page.goto('http://localhost:8765/src/index.html' + (args.includes('--guides') ? '?guides=1' : ''));
  await page.waitForFunction('window.ready === true', null, { timeout: 60000 });
  const tl = JSON.parse(fs.readFileSync(path.join(ROOT, 'build/timeline.json')));
  const stills = opt('--stills');
  if (stills) {
    fs.mkdirSync(path.join(ROOT, 'build/stills'), { recursive: true });
    for (const s of stills.split(',').map(Number)) {
      await page.evaluate(t => window.renderAt(t), s);
      await page.screenshot({ path: path.join(ROOT, `build/stills/t${s.toFixed(2)}.png`) });
      console.log('still', s);
    }
  } else {
    const fps = tl.fps, from = +(opt('--from') || 0), to = +(opt('--to') || tl.duration);
    const out = opt('--out') || path.join(ROOT, 'build/video_noaudio.mp4');
    const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const n = Math.round((to - from) * fps), t0 = Date.now();
    for (let f = 0; f < n; f++) {
      const t = from + f / fps;
      await page.evaluate(t => window.renderAt(t), t);
      const buf = await page.screenshot({ type: 'jpeg', quality: 95 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (f % 30 === 0) console.log(`frame ${f}/${n}  ${((Date.now() - t0) / 1000 / (f + 1)).toFixed(2)}s/frame`);
    }
    ff.stdin.end(); await new Promise(r => ff.on('close', r));
    console.log('wrote', out);
  }
  await browser.close(); server.close();
})();
