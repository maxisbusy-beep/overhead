/* Collect the web app into www/, which is what Capacitor bundles into the APK.
 *
 * The GitHub Pages site is still served straight from the repository root;
 * this only assembles a copy for the Android build. Run with: npm run build
 */
import { cp, mkdir, rm, stat } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const WWW = path.join(ROOT, 'www');

/* sw.js is deliberately left out: inside the APK every file is already local,
 * and a service worker there could serve a stale copy of the app after an
 * update. index.html only registers it on the web anyway. */
const ITEMS = ['index.html', 'manifest.webmanifest', 'icons'];

await rm(WWW, { recursive: true, force: true });
await mkdir(WWW, { recursive: true });

for (const item of ITEMS) {
  const from = path.join(ROOT, item);
  if (!existsSync(from)) {
    console.error(`build-www: missing ${item}`);
    process.exit(1);
  }
  await cp(from, path.join(WWW, item), { recursive: true });
  const s = await stat(from);
  console.log(`  ${item}${s.isDirectory() ? '/' : ''}`);
}

console.log(`build-www: wrote ${path.relative(ROOT, WWW)}/`);
