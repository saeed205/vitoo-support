/* The client's icons from the Vitoo mark (public/icon.svg), same pipeline as bridge/assets/make-icons.mjs.
     node remote-support/client/make-icons.mjs
   Needs the repo's Playwright (system Chrome). Outputs are committed in assets/, so CI never rasterises.
   The .ico is the bridge's (bridge/assets/vitoo.ico, 16-256 px), so the bridge and the support window match. */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const here = path.dirname(new URL(import.meta.url).pathname);
const root = path.join(here, '..', '..');
const out = path.join(here, 'assets');
const svg = fs.readFileSync(path.join(root, 'public', 'icon.svg'), 'utf8');
fs.mkdirSync(out, { recursive: true });

const browser = await chromium.launch({ channel: 'chrome' });
for (const s of [32, 64, 128, 256, 512]) {
  const page = await browser.newPage({ viewport: { width: 600, height: 600 } });
  const src = `data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}`;
  await page.setContent(`<html><body style="margin:0;background:transparent"><img style="display:block;width:${s}px;height:${s}px" src="${src}"></body></html>`);
  await page.waitForFunction(() => document.images[0].complete);
  fs.writeFileSync(path.join(out, `icon-${s}.png`), await page.locator('img').screenshot({ omitBackground: true }));
  await page.close();
}
await browser.close();
fs.copyFileSync(path.join(root, 'bridge', 'assets', 'vitoo.ico'), path.join(out, 'icon.ico'));
/* Flutter draws assets/icon.svg with flutter_svg: drop the fixed width/height so it scales to its box. */
fs.writeFileSync(path.join(out, 'icon.svg'), svg.replace(/\s(width|height)="\d+"/g, ''));
console.log('icons written to', path.relative(root, out));
