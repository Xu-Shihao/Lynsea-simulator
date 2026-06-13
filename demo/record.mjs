// Lynsea demo — Playwright driver + smoke test for the self-playing demo pages.
//
// Pages (all self-contained, 1280×720, auto-run & loop):
//   walkthrough.html  ~88s  full end-to-end walkthrough
//   teaser.html       ~15s  single-screen sizzle
//   pitch.html        ~30s  痛点 → 目标 → 技术 pitch
//   workflow.html     ~30s  condensed console → clarify → parallel-futures workflow
//
// DEFAULT — smoke test ALL pages (no files written):
//   node demo/record.mjs
//     Loads each page, runs one full loop, and FAILS LOUDLY (exit 1) on any
//     JS/console error OR if a page's late beat never lands (a real render bug).
//
// Capture frames for one page (for an MP4):
//   node demo/record.mjs --frames pitch        # → demo/frames/pitch/frame-XXXX.png
//   node demo/record.mjs --frames workflow
//
// Capture labelled beat stills for one page:
//   node demo/record.mjs --shots workflow      # → demo/frames/workflow/shot-XXs.png
//
// Make an MP4 from frames (optional):
//   ffmpeg -framerate 10 -i demo/frames/pitch/frame-%04d.png \
//          -c:v libx264 -pix_fmt yuv420p -r 30 -y demo/lynsea-pitch.mp4

import { chromium } from 'playwright';
import { fileURLToPath, pathToFileURL } from 'url';
import { dirname, join } from 'path';
import { mkdir } from 'fs/promises';

const __dirname = dirname(fileURLToPath(import.meta.url));
const url = name => pathToFileURL(join(__dirname, name + '.html')).href;

// Per-page config. `assert` is a CSS selector that must be present in the DOM at
// `checkAtMs` for the page's final beat to count as "landed".
const PAGES = {
  walkthrough: { durationMs: 88_000, fps: 10, beats: [3, 9, 14, 19, 24, 28, 35, 46, 52, 62, 80], checkAtMs: 53_000, assert: '#recstrip.in' },
  teaser:      { durationMs: 15_000, fps: 12, beats: [2, 4, 7, 10, 12, 14],                       checkAtMs: 13_800, assert: '#tagline.show' },
  pitch:       { durationMs: 30_000, fps: 10, beats: [3, 8, 13, 18, 23, 28],                       checkAtMs: 26_500, assert: '#beat-tech.show' },
  workflow:    { durationMs: 30_000, fps: 10, beats: [3, 8, 12, 15, 19, 23, 28],                   checkAtMs: 28_000, assert: '#recstrip.in' },
};

function arg(flag) { const i = process.argv.indexOf(flag); return i >= 0 ? process.argv[i + 1] : null; }
const FRAMES_PAGE = arg('--frames');
const SHOTS_PAGE = arg('--shots');

async function newPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 2 });
  const errors = [];
  page.on('pageerror', e => errors.push('[pageerror] ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('[console.error] ' + m.text()); });
  return { page, errors };
}

// Run one page through a single loop, asserting no errors and that its final beat lands.
async function smoke(browser, name) {
  const cfg = PAGES[name];
  const { page, errors } = await newPage(browser);
  await page.goto(url(name), { waitUntil: 'networkidle' });
  await page.waitForTimeout(cfg.checkAtMs);

  let landed = true, reason = '';
  try { await page.waitForSelector(cfg.assert, { timeout: 2_000, state: 'attached' }); }
  catch { landed = false; reason = `final beat selector "${cfg.assert}" never appeared`; }

  // let the rest of the loop play so we catch any late-firing errors too
  const remain = cfg.durationMs - cfg.checkAtMs - 2_000;
  if (remain > 0) await page.waitForTimeout(remain);
  await page.close();

  const ok = errors.length === 0 && landed;
  const label = `${name}.html (~${Math.round(cfg.durationMs / 1000)}s)`;
  if (ok) { console.log(`  ✓ ${label} — no errors, final beat landed`); }
  else {
    console.error(`  ✗ ${label} FAILED`);
    if (!landed) console.error(`      · ${reason}`);
    errors.forEach(e => console.error('      · ' + e));
  }
  return ok;
}

async function captureFrames(browser, name) {
  const cfg = PAGES[name];
  const out = join(__dirname, 'frames', name);
  await mkdir(out, { recursive: true });
  const { page, errors } = await newPage(browser);
  await page.goto(url(name), { waitUntil: 'networkidle' });
  await page.waitForTimeout(400);
  const total = Math.round((cfg.durationMs / 1000) * cfg.fps);
  const interval = 1000 / cfg.fps;
  for (let i = 0; i < total; i++) {
    await page.screenshot({ path: join(out, `frame-${String(i).padStart(4, '0')}.png`) });
    await page.waitForTimeout(interval);
  }
  await page.close();
  console.log(`captured ${total} frames at ${cfg.fps}fps → demo/frames/${name}/`);
  return errors;
}

async function captureShots(browser, name) {
  const cfg = PAGES[name];
  const out = join(__dirname, 'frames', name);
  await mkdir(out, { recursive: true });
  const { page, errors } = await newPage(browser);
  await page.goto(url(name), { waitUntil: 'networkidle' });
  await page.waitForTimeout(400);
  let last = 0;
  for (const sec of cfg.beats) {
    await page.waitForTimeout(sec * 1000 - last);
    last = sec * 1000;
    const file = `shot-${String(sec).padStart(2, '0')}s.png`;
    await page.screenshot({ path: join(out, file) });
    console.log('captured', name + '/' + file);
  }
  await page.close();
  return errors;
}

async function main() {
  const target = FRAMES_PAGE || SHOTS_PAGE;
  if (target && !PAGES[target]) {
    console.error(`unknown page "${target}". Known: ${Object.keys(PAGES).join(', ')}`);
    process.exit(2);
  }

  const browser = await chromium.launch();
  let errors = [];
  try {
    if (FRAMES_PAGE) {
      errors = await captureFrames(browser, FRAMES_PAGE);
    } else if (SHOTS_PAGE) {
      errors = await captureShots(browser, SHOTS_PAGE);
    } else {
      // default: smoke-test all pages
      console.log('Smoke-testing all demo pages (no errors + final beat must land)…\n');
      const results = [];
      for (const name of Object.keys(PAGES)) results.push(await smoke(browser, name));
      const allOk = results.every(Boolean);
      console.log(allOk ? '\n✓ all pages passed smoke test.' : '\n✗ smoke test failed.');
      await browser.close();
      process.exit(allOk ? 0 : 1);
    }
  } finally {
    await browser.close();
  }

  if (errors.length) {
    console.error('\n⚠ page errors detected:\n' + errors.join('\n'));
    process.exit(1);
  }
  console.log('\n✓ done — no page errors.');
}

main().catch(e => { console.error(e); process.exit(1); });
