// Lynsea demo — Playwright capture of the self-playing walkthrough.
//
// Drives demo/walkthrough.html in a 1280×720 viewport, lets the 60s
// animation run once, and writes a sequence of timestamped PNG frames.
// Stitching to MP4 (ffmpeg) is OPTIONAL — see demo/README.md. The final
// submission video can equally be a human screen-capture of the page.
//
// Usage:
//   npm i -D playwright            # or: npx playwright install chromium
//   node demo/record.mjs           # → demo/frames/frame-XXXX.png
//   node demo/record.mjs --shots   # → demo/frames/shot-<sec>.png at script beats only
//
// Make the MP4 (optional):
//   ffmpeg -framerate 10 -i demo/frames/frame-%04d.png \
//          -c:v libx264 -pix_fmt yuv420p -r 30 demo/lynsea-demo.mp4

import { chromium } from 'playwright';
import { fileURLToPath, pathToFileURL } from 'url';
import { dirname, join } from 'path';
import { mkdir } from 'fs/promises';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PAGE = pathToFileURL(join(__dirname, 'walkthrough.html')).href;
const OUT = join(__dirname, 'frames');

const SHOTS_ONLY = process.argv.includes('--shots');
const DURATION_MS = 60_000;
const FPS = 10;                       // full capture: 10 fps → 600 frames
// Key script beats (seconds) for --shots mode — mirror demo-script.md.
const BEATS = [4, 9, 13, 20, 27, 33, 40, 46, 52, 59];

async function main() {
  await mkdir(OUT, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 2 });

  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });

  await page.goto(PAGE, { waitUntil: 'networkidle' });
  await page.waitForTimeout(400);     // let fonts settle

  if (SHOTS_ONLY) {
    let last = 0;
    for (const sec of BEATS) {
      await page.waitForTimeout(sec * 1000 - last);
      last = sec * 1000;
      const name = `shot-${String(sec).padStart(2, '0')}s.png`;
      await page.screenshot({ path: join(OUT, name) });
      console.log('captured', name);
    }
  } else {
    const total = Math.round((DURATION_MS / 1000) * FPS);
    const interval = 1000 / FPS;
    for (let i = 0; i < total; i++) {
      await page.screenshot({ path: join(OUT, `frame-${String(i).padStart(4, '0')}.png`) });
      await page.waitForTimeout(interval);
    }
    console.log(`captured ${total} frames at ${FPS}fps`);
  }

  await browser.close();
  if (errors.length) {
    console.error('\n⚠ page errors detected:\n' + errors.join('\n'));
    process.exit(1);
  }
  console.log('\n✓ done — no page errors. Frames in demo/frames/.');
}

main().catch(e => { console.error(e); process.exit(1); });
